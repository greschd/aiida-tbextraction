#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from aiida.orm import DataFactory
from aiida.work.workchain import WorkChain
from aiida_tbmodels.work.bandevaluation import BandEvaluation

from .tbextraction import TbExtraction

class RunWindow(WorkChain):
    """
    This workchain runs the tight-binding extraction and analysis for a given energy window.
    """
    @classmethod
    def define(cls, spec):
        super(RunWindow, cls).define(spec)
        spec.input('window', valid_type=DataFactory('parameter'))
        spec.inherit_inputs(TbExtraction)
        spec.inherit_inputs(BandEvaluation, ignore=['tb_model'])

        spec.outline(
            self.extract_model, self.evaluate_bands, self.finalize
        )

    def extract_model(self):
        inputs = self.inherited_inputs(TbextractionWorkflow)
        # set the energy window
        wannier_settings = inputs.pop('wannier_settings').get_dict()
        wannier_settings.update(self.inputs.window.get_dict())
        inputs['wannier_settings'] = DataFactory('parameter')(dict=wannier_settings)
        return ToContext(
            tbextraction_calc=submit(TbExtraction, **inputs)
        )

    def evaluate_bands(self):
        inputs = BandEvaluation.get_inputs_template()
        inputs.update(self.inherited_inputs(BandEvaluation))
        tb_model = self.ctx.tbextraction_calc.out.tb_model
        inputs.tb_model = tb_model
        self.out('tb_model': tb_model)
        return ToContext(
            bandeval_calc=submit(BandEvaluation, **inputs)
        )

    def finalize(self):
        self.out('difference', self.ctx.bandeval_calc.out.difference)
