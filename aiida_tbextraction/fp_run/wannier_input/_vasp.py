from fsc.export import export
import numpy as np

from aiida.orm import Code, DataFactory, CalculationFactory
from aiida.work.workchain import ToContext
from aiida.work.process import PortNamespace

from aiida_tools import check_workchain_step

from . import WannierInputBase


@export  # pylint: disable=abstract-method
class VaspWannierInput(WannierInputBase):
    @classmethod
    def define(cls, spec):
        super(VaspWannierInput, cls).define(spec)

        ParameterData = DataFactory('parameter')
        spec.input('code', valid_type=Code)
        spec.input('parameters', valid_type=ParameterData)
        spec._inputs['calculation_kwargs'] = PortNamespace(
            'calculation_kwargs', required=False
        )

        spec.outline(cls.submit_calculation, cls.get_result)

    @check_workchain_step
    def submit_calculation(self):
        self.report("Submitting VASP2W90 calculation.")
        return ToContext(
            vasp_calc=self.submit(
                CalculationFactory('vasp.vasp2w90').process(),
                structure=self.inputs.structure,
                paw=self.inputs.potentials,
                kpoints=self.inputs.kpoints_mesh,
                parameters=self.inputs.parameters,
                code=self.inputs.code,
                wannier_parameters=self.inputs.get('wannier_parameters', None),
                wannier_projections=self.inputs.
                get('wannier_projections', None),
                **self.inputs.get('calculation_kwargs', {})
            )
        )

    @check_workchain_step
    def get_result(self):
        self.out(
            'wannier_settings',
            DataFactory('parameter')(dict={
                'seedname': 'wannier90'
            })
        )
        vasp_calc_output = self.ctx.vasp_calc.out
        retrieved_folder = vasp_calc_output.retrieved
        folder_list = retrieved_folder.get_folder_list()
        assert all(
            filename in folder_list
            for filename in
            ['wannier90.amn', 'wannier90.mmn', 'wannier90.eig']
        )
        self.report("Adding Wannier90 inputs to output.")
        self.out('wannier_input_folder', retrieved_folder)
        self.out('wannier_parameters', vasp_calc_output.wannier_parameters)
        assert np.allclose(
            vasp_calc_output.wannier_kpoints.get_kpoints(),
            vasp_calc_output.bands.get_kpoints()
        )
        self.out('wannier_bands', vasp_calc_output.bands)
        self.out('wannier_projections', vasp_calc_output.wannier_projections)
