#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from aiida.orm import DataFactory
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext
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
        spec.inherit_inputs(BandEvaluation, exclude=['tb_model'])

        spec.outline(
            cls.extract_model, cls.evaluate_bands, cls.finalize
        )

    def extract_model(self):
        inputs = self.inherited_inputs(TbExtraction)
        # set the energy window
        wannier_parameters = inputs.pop('wannier_parameters').get_dict()
        wannier_parameters.update(self.inputs.window.get_dict())
        inputs['wannier_parameters'] = DataFactory('parameter')(dict=wannier_parameters)
        self.report("Extracting tight-binding model...")
        return ToContext(
            tbextraction_calc=submit(TbExtraction, **inputs)
        )

    def evaluate_bands(self):
        tb_model = self.ctx.tbextraction_calc.out.tb_model
        self.report("Adding tight-binding model to output.")
        self.out('tb_model', tb_model)
        self.report("Running band evaluation...")
        return ToContext(bandeval_calc=submit(
            BandEvaluation,
            tb_model=tb_model,
            **self.inherited_inputs(BandEvaluation)
        ))

    def finalize(self):
        self.report("Adding band difference to output.")
        self.out('difference', self.ctx.bandeval_calc.out.difference)
