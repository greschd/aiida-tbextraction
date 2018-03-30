"""
Defines a workflow for running the first-principles calculations using VASP.
"""

import copy
try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.work.workchain import ToContext
from aiida.orm.code import Code
from aiida.orm.data.base import Bool
from aiida.orm.data.parameter import ParameterData

from aiida_vasp.calcs.vasp import VaspCalculation

from aiida_tools import check_workchain_step

from .wannier_input import VaspWannierInput
from .reference_bands import VaspReferenceBands
from ._base import FirstPrinciplesRunBase
from ._helpers._inline_calcs import merge_parameters_inline


@export
class VaspFirstPrinciplesRun(FirstPrinciplesRunBase):
    """
    Workflow for calculating the inputs needed for tight-binding calculation and evaluation with VASP. The workflow first performs an SCF step, and then passes the WAVECAR file to the bandstructure and Wannier90 input calculations.
    """

    @classmethod
    def define(cls, spec):
        super(VaspFirstPrinciplesRun, cls).define(spec)

        # Top-level parameters
        spec.input('code', valid_type=Code)
        spec.input('parameters', valid_type=ParameterData)
        spec.input_namespace(
            'calculation_kwargs', required=False, dynamic=True
        )

        # Optional parameters to override for specific calculations.
        # TODO: Use expose for the sub-workflows.
        for sub_calc in ['scf', 'bands', 'to_wannier']:
            spec.input_namespace(sub_calc, required=False, dynamic=True)

        spec.input('bands.merge_kpoints', valid_type=Bool, default=Bool(False))

        spec.expose_outputs(VaspReferenceBands)
        spec.expose_outputs(VaspWannierInput)

        spec.outline(cls.run_scf, cls.run_bands_and_wannier, cls.finalize)

    def _collect_common_inputs(
        self, namespace, expand_kwargs=False, force_parameters=None
    ):
        """
        Join the top-level inputs and inputs set in a specific namespace.
        """
        ns_inputs = self.inputs.get(namespace, {})
        ns_parameters = ns_inputs.get('parameters')
        if ns_parameters is None:
            parameters = self.inputs.parameters
        else:
            parameters = merge_parameters_inline(
                param_main=ns_parameters,
                param_fallback=self.inputs.parameters
            )[1]['parameters']
            if force_parameters:
                parameters = merge_parameters_inline(
                    param_main=ParameterData(dict=force_parameters),
                    param_fallback=parameters
                )[1]['parameters']
        calculation_kwargs = copy.deepcopy(
            dict(
                ChainMap(
                    ns_inputs.get('calculation_kwargs', {}),
                    self.inputs.calculation_kwargs
                )
            )
        )
        res = dict(
            code=self.inputs.code,
            structure=self.inputs.structure,
            parameters=parameters,
        )
        if expand_kwargs:
            res.update(calculation_kwargs)
        else:
            res['calculation_kwargs'] = calculation_kwargs
        return res

    @check_workchain_step
    def run_scf(self):
        """
        Run the SCF calculation step.
        """
        self.report('Launching SCF calculation.')
        return ToContext(
            scf=self.submit(
                VaspCalculation.process(),
                paw=self.inputs.potentials,
                kpoints=self.inputs.kpoints_mesh,
                settings=ParameterData(
                    dict={
                        'ADDITIONAL_RETRIEVE_LIST': ['WAVECAR']
                    }
                ),
                **self._collect_common_inputs(
                    'scf',
                    force_parameters={'lwave': True},
                    expand_kwargs=True
                )
            )
        )

    def _collect_workchain_inputs(self, namespace):
        """
        Helper to collect the inputs for the reference bands and wannier input workflows.
        """
        scf_wavefun = self.ctx.scf.out.wavefunctions
        res = self._collect_common_inputs(namespace)
        res['potentials'] = self.inputs.potentials
        res['calculation_kwargs']['wavefunctions'] = scf_wavefun
        self.report(res['calculation_kwargs'])
        return res

    @check_workchain_step
    def run_bands_and_wannier(self):
        """
        Run the reference bands and wannier input workflows.
        """
        self.report('Launching bands and to_wannier workchains.')
        return ToContext(
            bands=self.submit(
                VaspReferenceBands,
                kpoints=self.inputs.kpoints,
                kpoints_mesh=self.inputs.kpoints_mesh,
                merge_kpoints=self.inputs.bands['merge_kpoints'],
                **self._collect_workchain_inputs('bands')
            ),
            to_wannier=self.submit(
                VaspWannierInput,
                kpoints_mesh=self.inputs.kpoints_mesh,
                wannier_parameters=self.inputs.get('wannier_parameters', None),
                wannier_projections=self.inputs.get(
                    'wannier_projections', None
                ),
                **self._collect_workchain_inputs('to_wannier')
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add outputs of the bandstructure and wannier input calculations.
        """
        self.report('Checking that the bands calculation used WAVECAR.')
        self.check_read_wavecar(self.ctx.bands)

        self.report(
            'Checking that the wannier input calculation used WAVECAR.'
        )
        self.check_read_wavecar(self.ctx.to_wannier)

        self.report('Retrieving outputs.')
        self.out_many(self.exposed_outputs(self.ctx.bands, VaspReferenceBands))
        self.out_many(
            self.exposed_outputs(self.ctx.to_wannier, VaspWannierInput)
        )

    @staticmethod
    def check_read_wavecar(sub_workflow):
        for label, node in sub_workflow.get_outputs(also_labels=True):
            if label == 'CALL' and isinstance(node, VaspCalculation):
                retrieved_folder = node.get_retrieved_node()
                with open(
                    retrieved_folder.get_abs_path('_scheduler-stdout.txt')
                ) as f:
                    stdout = f.read()
                    assert 'WAVECAR not read' not in stdout
                    assert 'reading WAVECAR' in stdout
