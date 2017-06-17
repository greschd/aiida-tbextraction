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
            if_(cls.has_slice)(cls.run_slice),
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
        pid = submit(
            CalculationFactory('vasp.wswannier').process(),
            code=self.inputs.wannier_code,
            _options=dict(resources=dict(num_machines=1, tot_num_mpiprocs=1), queue_name=self.inputs.wannier_queue.value),
            # queue_name=self.inputs.wannier_queue,
            data=self.inputs.wannier_data,
            settings=DataFactory('parameter')(dict=wannier_settings)
        )
        return ToContext(wannier_output=pid)

    def parse(self):
        raise NotImplemented

    def run_slice(self):
        raise NotImplemented

    def symmetrize(self):
        raise NotImplemented

    def finalize(self):
        raise NotImplemented
