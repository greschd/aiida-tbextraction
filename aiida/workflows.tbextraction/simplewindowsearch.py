#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Author:  Dominik Gresch <greschd@gmx.ch>

# from past.builtins import basestring
from aiida_tools.validate_input import validate_input, parameter, inherit_parameters
from aiida.orm import (
    Code, Computer, DataFactory, CalculationFactory, QueryBuilder, Workflow, WorkflowFactory
)

from .runwindow import RunwindowWorkflow

@validate_input
@parameter('window_parameters', DataFactory('parameter'))
@inherit_parameters(RunwindowWorkflow, ignore=['window'])
class SimplewindowsearchWorkflow(Workflow):
    """
    This workflow runs a series of possible energy windows and selects the best-matching tight-binding model.
    """
    def __init__(self, **kwargs):
        super(SimplewindowsearchWorkflow, self).__init__(**kwargs)

    def _count_bands(self, limits):
        lower, upper = sorted(limits)
        bands = self.get_parameter('reference_bands').get_bands()
        band_count = np.sum(
            np.logical_and(lower <= bands, bands <= upper),
            axis=-1
        )
        return np.min(band_count), np.max(band_count)

    def _window_valid(self, window):
        win_min = window['dis_win_min']
        win_max = window['dis_win_max']
        froz_min = window['dis_froz_min']
        froz_max = window['dis_froz_max']
        num_wann = self.get_parameter('wannier_settings')['num_wann']

        # max >= min
        if win_min > win_max or froz_min > froz_max:
            return False

        # outer window contains the inner window
        if win_min > froz_min or win_max < froz_max:
            return False

        # check number of bands in froz <= num_wann
        if self._count_bands(limits=(froz_min, froz_max))[1] > num_wann:
            return False
        # check number of bands in win >= num_wann
        if self._count_bands(limits=(win_min, win_max))[0] < num_wann:
            return False
        return True

    @Workflow.step
    def start(self):
        window_params = self.get_parameter('window_parameters')
        window_keys = sorted(window_params.keys())
        all_windows = [
            {k: v for k, v in zip(window_keys, vals)}
            for vals in itertools.product(*[window_params[key] for key in window_keys])
        ]
        runwindow_params = self.inherited_parameters(RunwindowWorkflow)
        for window in all_windows:
            if self._window_valid(window):
                params = copy.copy(runwindow_params)
                params['window'] = DataFactory('parameter')(dict=window)
                wf = RunwindowWorkflow(params=params)
                wf.store()
                wf.start()
                self.attach_workflow(wf)

        self.next(self.finalize)

    @Workflow.step
    def finalize(self):
        # find best result for the difference
