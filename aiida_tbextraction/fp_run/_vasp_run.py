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

    def _collect_common_inputs(self, namespace, expand_kwargs=False):
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
        calculation_kwargs = copy.deepcopy(
            dict(
                ChainMap(
                    ns_inputs.get('calculation_kwargs', {}),
                    self.inputs.calculation_kwargs
                )
            )
        )
        self.report(calculation_kwargs)
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
                **self._collect_common_inputs('scf', expand_kwargs=True)
            )
        )

    def _collect_workchain_inputs(self, namespace):
        scf_wavefun = self.ctx.scf.out.wavefunctions
        res = self._collect_common_inputs(namespace)
        res['potentials'] = self.inputs.potentials
        res['calculation_kwargs']['wavefunctions'] = scf_wavefun
        self.report(res['calculation_kwargs'])
        return res

    @check_workchain_step
    def run_bands_and_wannier(self):
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
        self.report('Retrieving outputs.')
        self.out_many(self.exposed_outputs(self.ctx.bands, VaspReferenceBands))
        self.out_many(
            self.exposed_outputs(self.ctx.to_wannier, VaspWannierInput)
        )