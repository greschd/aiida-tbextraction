#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from past.builtins import basestring
from aiida_tools.validate_input import validate_input, parameter, inherit_parameters
from aiida.orm import (
    Code, Computer, DataFactory, CalculationFactory, QueryBuilder, Workflow, WorkflowFactory
)

from .tbextraction import TbextractionWorkflow
BandevaluationWorkflow = WorkflowFactory('tbmodels.bandevaluation')

@validate_input
@parameter('window', DataFactory('parameter'))
@inherit_parameters(BandevaluationWorkflow, ignore=['tb_model'])
@inherit_parameters(TbextractionWorkflow)
class RunwindowWorkflow(Workflow):
    """
    This workflow runs the tight-binding extraction and analysis for a given energy window.
    """
    def __init__(self, **kwargs):
        super(RunwindowWorkflow, self).__init__(**kwargs)

    @Workflow.step
    def start(self):
        extraction_params = self.inherited_parameters(TbextractionWorkflow)
        # set the energy window
        wannier_settings = extraction_params['wannier_settings'].get_dict()
        wannier_settings.update(self.get_parameter('window').get_dict())
        wannier_settings_data = DataFactory('parameter')(dict=wannier_settings)
        wannier_settings_data.store()
        extraction_params['wannier_settings'] = wannier_settings_data
        wf = TbextractionWorkflow(params=extraction_params)
        wf.store()
        wf.start()
        self.attach_workflow(wf)
        self.next(self.bandeval)

    @Workflow.step
    def bandeval(self):
        extraction_wf = self.get_step_workflows(self.start)[0]
        band_params = self.inherited_parameters(BandevaluationWorkflow)
        # set the tight-binding model from the extraction
        tb_model = extraction_wf.get_result('tb_model')
        band_params['tb_model'] = tb_model
        self.add_result('tb_model', tb_model)
        wf = BandevaluationWorkflow(params=band_params)
        wf.store()
        wf.start()
        self.attach_workflow(wf)
        self.next(self.finalize)

    @Workflow.step
    def finalize(self):
        eval_wf = self.get_step_workflows(self.bandeval)[0]
        self.add_result('difference', eval_wf.get_result('difference'))
        self.next(self.exit)
