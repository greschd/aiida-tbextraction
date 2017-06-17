#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from aiida.orm.data.base import Str
from aiida.work.workchain import WorkChain, if_
from aiida.orm import (
    Code, Computer, DataFactory, CalculationFactory
)

class TbExtraction(WorkChain):
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
            cls.parse,
            if_(cls.has_slice, cls.run_slice),
            if_(cls.has_symmetries, cls.symmetrize),
            cls.finalize
        )

    def has_slice(self):
        return 'slice_idx' in self.inputs

    def has_symmetries(self):
        return 'symmetries' in self.inputs
