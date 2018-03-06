try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process import PortNamespace
from aiida.orm.code import Code
from aiida.orm.data.base import Bool
from aiida.orm.data.parameter import ParameterData

from aiida_vasp.calcs.vasp import VaspCalculation
from aiida_vasp.calcs.vasp2w90 import Vasp2w90Calculation

from aiida_tools import check_workchain_step

from .wannier_input import VaspWannierInput
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
        spec.input('calculation_kwargs', valid_type=ParameterData)

        # Optional parameters to override for specific calculations.
        for sub_calc in ['scf', 'bands', 'to_wannier']:
            for input_name in ['parameters', 'calculation_kwargs']:
                spec.input(
                    '{}.{}'.format(sub_calc, input_name),
                    valid_type=ParameterData,
                    required=False
                )
        spec.input('bands.join_kpoints', valid_type=Bool, default=Bool(False))

        spec.outline(cls.run_scf, cls.run_bands_and_wannier, cls.finalize)

    def collect_inputs(self, namespace):
        """
        Join the top-level inputs and inputs set in a specific namespace.
        """
        ns_parameters = self.inputs.get(namespace + '.parameters')
        if ns_parameters is None:
            parameters = self.inputs.parameters
        else:
            parameters = merge_parameters_inline(
                ns_parameters, self.inputs.parameters
            )['parameters']
        calculation_kwargs = ChainMap(
            self.inputs.get(
                namespace + '.calculation_kwargs', ParameterData(dict={})
            ).get_dict(), self.inputs.calculation_kwargs.get_dict()
        )
        return dict(
            code=self.inputs.code,
            structure=self.inputs.structure,
            paw=self.inputs.potentials,
            parameters=parameters,
            **calculation_kwargs
        )

    @check_workchain_step
    def run_scf(self):
        return ToContext(
            scf=submit(
                VaspCalculation.process(),
                kpoints=self.inputs.kpoints_mesh,
                **self.collect_inputs('scf')
            )
        )

    @check_workchain_step
    def run_bands_and_wannier(self):
        # return ToContext(
        #     bands=submit(
        #         VaspCalculation.process(),
        #         wavefunctions=,
        #         kpoints=..,
        #         **self.collect_inputs('bands')
        #     ),
        #     to_wannier=submit(
        #         Vasp2w90Calculation.process(),
        #         kpoints=self.inputs.kpoints_mesh,
        #         wavefunctions=
        #         wannier_parameters=self.inputs.get('wannier_parameters', None),
        #         wannier_projections=self.inputs.get('wannier_projections', None),
        #         **self.collect_inputs('to_wannier')
        #     )
        # )
        pass

    @check_workchain_step
    def finalize(self):
        pass
