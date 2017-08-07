#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida.work.run import submit
from aiida.orm import DataFactory, CalculationFactory
from aiida.work.workchain import ToContext

from .base import ToWannier90Base

class VaspToWannier90(ToWannier90Base):
    @classmethod
    def define(cls, spec):
        super(VaspToWannier90, cls).define(spec)
        spec.outline(
            cls.submit_calculation, cls.get_result
        )

    def submit_calculation(self):
        self.report("Submitting VASP2W90 calculation.")
        return ToContext(
            vasp_calc=submit(
                CalculationFactory('vasp.vasp2w90').process(),
                structure=self.inputs.structure,
                paw=self.inputs.potentials,
                kpoints=self.inputs.kpoints_mesh,
                parameters=self.inputs.parameters,
                code=self.inputs.code,
                wannier_parameters=self.inputs.get('wannier_parameters', None),
                wannier_projections=self.inputs.get('wannier_projections', None),
                **self.inputs.calculation_kwargs.get_dict()
        ))

    def get_result(self):
        self.report("Adding Wannier90 input folder to output.")
        vasp_calc_output = self.ctx.vasp_calc.out
        retrieved_folder = vasp_calc_output.retrieved
        folder_list = retrieved_folder.get_folder_list()
        assert all(filename in folder_list for filename in [
            'wannier90.amn', 'wannier90.mmn', 'wannier90.eig'
        ])
        self.out('wannier_input_folder', retrieved_folder)
        self.out('wannier_parameters', vasp_calc_output.wannier_parameters)
