#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from aiida.orm.data.base import Str
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, if_, ToContext
from aiida.orm import (
    Code, Computer, DataFactory, CalculationFactory
)

class TbExtraction(WorkChain):
    """
    This workchain takes a Wannier90 input and a symmetry file as input and returns the symmetrized TBmodels model.
    """
    @classmethod
    def define(cls, spec):
        super(TbExtraction, cls).define(spec)

        spec.input('wannier_code', valid_type=Code)
        spec.input('wannier_data', valid_type=DataFactory('vasp.archive'))
        spec.input('wannier_queue', valid_type=Str)
        spec.input('wannier_settings', valid_type=DataFactory('parameter'))

        spec.input('tbmodels_code', valid_type=Code)

        spec.input('slice_idx', valid_type=DataFactory('tbmodels.list'), required=False)
        spec.input('symmetries', valid_type=DataFactory('singlefile'), required=False)

        spec.outline(
            cls.run_wswannier,
            cls.parse,
            if_(cls.has_slice)(cls.slice),
            if_(cls.has_symmetries)(cls.symmetrize),
            cls.finalize
        )

    def has_slice(self):
        return 'slice_idx' in self.inputs

    def has_symmetries(self):
        return 'symmetries' in self.inputs

    def run_wswannier(self):
        wannier_settings = self.inputs.wannier_settings.get_dict()
        wannier_settings.setdefault('write_hr', True)
        wannier_settings.setdefault('use_ws_distance', True)
        print("Running Wannier90 calculation...")
        pid = submit(
            CalculationFactory('vasp.wswannier').process(),
            code=self.inputs.wannier_code,
            _options=dict(resources=dict(num_machines=1, tot_num_mpiprocs=1), queue_name=self.inputs.wannier_queue.value),
            # queue_name=self.inputs.wannier_queue,
            data=self.inputs.wannier_data,
            settings=DataFactory('parameter')(dict=wannier_settings)
        )
        return ToContext(wannier_calc=pid)

    def setup_tbmodels(self, calc_string):
        process = CalculationFactory(calc_string).process()
        inputs = process.get_inputs_template()
        inputs.code = self.inputs.tbmodels_code
        inputs._options.resources = {'num_machines': 1}
        inputs._options.withmpi = False
        return process, inputs

    @property
    def tb_model(self):
        return self.ctx.tbmodels_calc.out.tb_model

    def parse(self):
        process, inputs = self.setup_tbmodels('tbmodels.parse')
        inputs.wannier_folder = self.ctx.wannier_calc.out.tb_model
        print("Parsing Wannier90 output to tbmodels format...")
        pid = submit(
            process,
            **inputs
        )
        return ToContext(tbmodels_calc=pid)

    def slice(self):
        process, inputs = self.setup_tbmodels('tbmodels.slice')
        inputs.tb_model = self.tb_model
        inputs.slice_idx = self.inputs.slice_idx
        print("Slicing tight-binding model...")
        pid = submit(
            process,
            **inputs
        )
        return ToContext(tbmodels_calc=pid)

    def symmetrize(self):
        process, inputs = self.setup_tbmodels('tbmodels.symmetrize')
        inputs.tb_model = self.tb_model
        inputs.symmetries = self.inputs.symmetries
        print("Symmetrizing tight-binding model...")
        pid = submit(
            process,
            **inputs
        )
        return ToContext(tbmodels_calc=pid)

    def finalize(self):
        self.out("tb_model", self.tb_model)
        print('Added final tb_model to results.')
