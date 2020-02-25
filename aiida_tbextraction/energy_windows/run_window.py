# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow for running the tight-binding calculation and evaluation for a given energy window.
"""

from collections import ChainMap

import numpy as np

from aiida import orm
from aiida.engine import WorkChain, ToContext, if_, calcfunction

from aiida_tools import check_workchain_step, get_outputs_dict
from aiida_tools.process_inputs import PROCESS_INPUT_KWARGS, load_object

from ..model_evaluation import ModelEvaluationBase
from ..calculate_tb import TightBindingCalculation

__all__ = ('RunWindow', )


class RunWindow(WorkChain):
    """
    This workchain runs the tight-binding extraction and analysis for a given energy window.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(TightBindingCalculation)
        spec.expose_inputs(ModelEvaluationBase, exclude=['tb_model'])
        spec.input_namespace(
            'model_evaluation',
            dynamic=True,
            help=
            'Inputs that will be passed to the ``model_evaluation_workflow``.'
        )

        spec.input(
            'window',
            valid_type=orm.List,
            help=
            'Disentaglement energy windows used by Wannier90, given as a list ``[dis_win_min, dis_froz_min, dis_froz_max, dis_win_max]``.'
        )
        spec.input(
            'wannier_bands',
            valid_type=orm.BandsData,
            help=
            "Parsed band structure from the ``*.eig`` file, used to determine "
            "if the given energy window is valid. Note that this input is "
            "assumed to be consistent with the ``*.eig`` file given in "
            "'wannier.{local,remote}_input_folder'."
        )
        spec.input(
            'model_evaluation_workflow',
            help=
            'AiiDA workflow that will be used to evaluate the tight-binding model.',
            **PROCESS_INPUT_KWARGS
        )

        spec.expose_outputs(ModelEvaluationBase)
        spec.outputs.dynamic = True
        spec.outline(
            if_(cls.window_valid
                )(cls.calculate_model, cls.evaluate_bands, cls.finalize),
            if_(cls.window_invalid)(cls.abort_invalid)
        )

    @check_workchain_step
    def window_invalid(self):
        """
        Check if a window is invalid.
        """
        return not self.window_valid(show_msg=False)

    @check_workchain_step
    def window_valid(self, show_msg=True):
        """
        Check if a window is valid.
        """
        window_list = self.inputs.window.get_list()
        win_min, froz_min, froz_max, win_max = window_list
        num_wann = int(
            self.inputs.wannier.parameters.get_attribute('num_wann')
        )

        window_invalid_str = 'Window [{}, ({}, {}), {}] is invalid'.format(
            *window_list
        )

        # window values must be sorted
        if sorted(window_list) != window_list:
            if show_msg:
                self.report(
                    '{}: windows values not sorted.'.
                    format(window_invalid_str)
                )
            return False

        # check number of bands in inner window <= num_wann
        if np.max(self._count_bands(limits=(froz_min, froz_max))) > num_wann:
            if show_msg:
                self.report(
                    '{}: Too many bands in inner window.'.
                    format(window_invalid_str)
                )
            return False
        # check number of bands in outer window >= num_wann
        if np.min(self._count_bands(limits=(win_min, win_max))) < num_wann:
            if show_msg:
                self.report(
                    '{}: Too few bands in outer window.'.
                    format(window_invalid_str)
                )
            return False
        return True

    def _count_bands(self, limits):
        """
        Count the number of bands within the given limits.
        """
        lower, upper = sorted(limits)
        bands = self.inputs.wannier_bands.get_bands()
        band_count = np.sum(
            np.logical_and(lower <= bands, bands <= upper), axis=-1
        )
        return band_count

    @check_workchain_step
    def calculate_model(self):
        """
        Run the tight-binding calculation workflow.
        """
        inputs = self.exposed_inputs(TightBindingCalculation)
        # set the energy window
        inputs['wannier']['parameters'] = add_window_parameters_calcfunc(
            parameters=inputs['wannier']['parameters'],
            window=self.inputs.window
        )
        self.report("Calculating tight-binding model.")
        return ToContext(
            tbextraction_calc=self.submit(TightBindingCalculation, **inputs)
        )

    @check_workchain_step
    def evaluate_bands(self):
        """
        Add the tight-binding model to the outputs and run the evaluation workflow.
        """
        self.report("Adding tight-binding model to output.")
        tb_model = self.ctx.tbextraction_calc.outputs.tb_model
        self.out('tb_model', tb_model)
        self.report("Running model evaluation.")
        return ToContext(
            model_evaluation_wf=self.submit(
                load_object(self.inputs.model_evaluation_workflow),
                tb_model=tb_model,
                **ChainMap(
                    self.inputs.model_evaluation,
                    self.exposed_inputs(ModelEvaluationBase),
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the evaluation outputs.
        """
        self.report("Retrieving model evaluation outputs.")
        self.out_many(get_outputs_dict(self.ctx.model_evaluation_wf))

    @check_workchain_step
    def abort_invalid(self):
        """
        Abort when an invalid window is found. The 'cost_value' is set to a
        very large number. Infinity cannot be serialized into the AiiDA
        database.
        """
        self.report('Window is invalid, assigning very large cost_value.')
        self.out('cost_value', orm.Float(314159265358979323).store())


@calcfunction
def add_window_parameters_calcfunc(parameters, window):
    """
    Adds the window values to the given Wannier90 input parameters.
    """
    param_dict = parameters.get_dict()
    win_min, froz_min, froz_max, win_max = window.get_list()
    param_dict.update(
        dict(
            dis_win_min=win_min,
            dis_win_max=win_max,
            dis_froz_min=froz_min,
            dis_froz_max=froz_max,
        )
    )
    return orm.Dict(dict=param_dict)
