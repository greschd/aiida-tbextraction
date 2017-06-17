#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

from aiida_tools.validate_input import validate_input, parameter
from past.builtins import basestring
from aiida.orm import (
    Code, Computer, DataFactory, CalculationFactory, QueryBuilder, Workflow
)

@validate_input
@parameter('wannier_code', type=basestring)
@parameter('wannier_data', type=DataFactory('vasp.archive'))
@parameter('wannier_queue', type=basestring)
@parameter('wannier_settings', type=DataFactory('parameter'))
@parameter('tbmodels_code', type=basestring)
@parameter('slice_idx', type=DataFactory('tbmodels.list'), required=False)
@parameter('symmetries', type=DataFactory('singlefile'), required=False)
class TbextractionWorkflow(Workflow):
    """
    This workflow takes a Wannier90 input and a symmetry file as input and returns the symmetrized TBmodels model.
    """
    def __init__(self, **kwargs):
        super(TbextractionWorkflow, self).__init__(**kwargs)

    @Workflow.step
    def start(self):
        params = self.get_parameters()
        self.add_attribute('has_slice', 'slice_idx' in params)
        self.add_attribute('has_symmetries', 'symmetries' in params)

        extra_steps = ['parse']
        if self.get_attribute('has_slice'):
            extra_steps += ['slice']
        if self.get_attribute('has_symmetries'):
            extra_steps += ['symmetrize']
        extra_steps += ['finalize']
        self.add_attribute('steps_todo', extra_steps)
        self.add_attribute('steps_done', [])

        self.next(self.wannier)

    @property
    def previous_step(self):
        return eval('self.' + self.get_attribute('steps_done')[-1])

    def get_next_step(self):
        # This is a bit of a hack -- but it enables chaining the steps without
        # having to write lots of logic to detect which was the previous step
        # For it to work, get_next_step must be used in the self.next call.
        steps_todo = self.get_attribute('steps_todo')
        steps_done = self.get_attribute('steps_done')
        try:
            current_step = self.get_attribute('current_step')
            steps_done += [current_step]
        except ValueError:
            pass

        current_step = steps_todo.pop(0)
        self.add_attribute('current_step', current_step)
        self.add_attribute('steps_todo', steps_todo)
        self.add_attribute('steps_done', steps_done)
        return eval('self.' + current_step)

    def run_wswannier(self):
        input_archive = self.get_parameter('wannier_data')
        calc = CalculationFactory('vasp.wswannier')()
        code = Code.get_from_string(self.get_parameter('wannier_code'))
        calc.use_code(code)
        # No MPI
        calc.set_resources(dict(num_machines=1, tot_num_mpiprocs=1))
        calc.set_computer(code.get_computer())
        calc.set_queue_name(self.get_parameter('wannier_queue'))
        calc.use_data(input_archive)
        # set default for write_tb etc.
        wannier_settings = self.get_parameter('wannier_settings').get_dict()
        wannier_settings.setdefault('write_hr', True)
        # wannier_settings.setdefault('write_xyz', True)
        wannier_settings.setdefault('use_ws_distance', True)
        # TODO: caching!
        calc.use_settings(DataFactory('parameter')(dict=wannier_settings))
        calc.store_all()
        return calc

    @Workflow.step
    def wannier(self):
        self.append_to_report("Running Wannier90 calculation...")
        self.attach_calculation(self.run_wswannier())
        self.next(self.get_next_step())

    def setup_tbmodels(self, calc):
        code = Code.get_from_string(self.get_parameter('tbmodels_code'))
        calc.use_code(code)
        calc.set_resources({'num_machines': 1})
        calc.set_withmpi(False)
        calc.set_computer(code.get_computer())

    def run_parse(self, wannier_folder):
        calc = CalculationFactory('tbmodels.parse')()
        self.setup_tbmodels(calc)

        calc.use_wannier_folder(wannier_folder)
        calc.store_all()
        return calc

    @Workflow.step
    def parse(self):
        wannier_calc = self.get_step_calculations(self.wannier)[0]
        wannier_folder = wannier_calc.out.tb_model
        self.append_to_report("Parsing Wannier90 output to tbmodels format...")
        self.attach_calculation(self.run_parse(wannier_folder))
        self.next(self.get_next_step())

    def run_slice(self, tbmodel_file):
        calc = CalculationFactory('tbmodels.slice')()
        self.setup_tbmodels(calc)
        calc.use_tb_model(tbmodel_file)
        calc.use_slice_idx(self.get_parameter("slice_idx"))
        calc.store_all()
        return calc

    @Workflow.step
    def slice(self):
        calc = self.get_step_calculations(self.previous_step)[0]
        tbmodel_file = calc.out.tb_model
        self.append_to_report("Slicing tight-binding model...")
        self.attach_calculation(self.run_slice(tbmodel_file))
        self.next(self.get_next_step())

    def run_symmetrize(self, tbmodel_file):
        calc = CalculationFactory('tbmodels.symmetrize')()
        self.setup_tbmodels(calc)
        calc.use_tb_model(tbmodel_file)
        calc.use_symmetries(self.get_parameter("symmetries"))
        calc.store_all()
        return calc

    @Workflow.step
    def symmetrize(self):
        calc = self.get_step_calculations(self.previous_step)[0]
        tbmodel_file = calc.out.tb_model
        self.append_to_report("Symmetrizing tight-binding model...")
        self.attach_calculation(self.run_symmetrize(tbmodel_file))
        self.next(self.get_next_step())

    @Workflow.step
    def finalize(self):
        calc = self.get_step_calculations(self.previous_step)[0]
        self.add_result('tb_model', calc.out.tb_model)
        self.append_to_report('Added final tb_model to results.')
        self.next(self.exit)
