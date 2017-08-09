#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
import itertools

import numpy as np
from aiida.orm import DataFactory
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, while_

from .runwindow import RunWindow

class WindowSearch(WorkChain):
    """
    This workchain runs a series of possible energy windows and selects the best-matching tight-binding model.
    """
    @classmethod
    def define(cls, spec):
        super(WindowSearch, cls).define(spec)

        spec.inherit_inputs(RunWindow, exclude=['window', 'wannier_kpoints'])
        spec.input('window_values', valid_type=DataFactory('parameter'))
        spec.input('wannier_bands', valid_type=DataFactory('array.bands'))

        # TODO: Generalize to allow iterative window search
        spec.outline(
            cls.run_windows, cls.check_windows
        )

    def run_windows(self):
        valid_windows = self._get_valid_windows()
        if not valid_windows:
            self.report('No valid energy windows found, aborting.')
            raise AssertionError
        runwindow_inputs = self.inherited_inputs(RunWindow)
        window_runs = []
        wannier_kpoints = self.inputs.wannier_bands
        for window in valid_windows:
            inputs = copy.copy(runwindow_inputs)
            inputs['window'] = DataFactory('parameter')(dict=window)
            inputs['wannier_kpoints'] = wannier_kpoints
            self.report('Submitting calculation with window={}.'.format(window))
            pid = submit(RunWindow, **inputs)
            window_runs.append(pid)
        return self.to_context(**{
            'window_{}'.format(i): pid
            for i, pid in enumerate(window_runs)
        })

    def _get_valid_windows(self):
        window_values = self.inputs.window_values.get_dict()
        all_windows = [
            {key: val for key, val in zip(window_values.keys(), window_choice)}
            for window_choice in itertools.product(*window_values.values())
        ]
        return [
            window for window in all_windows
            if self._window_is_valid(window)
        ]

    def _window_is_valid(self, window):
        win_min = window['dis_win_min']
        win_max = window['dis_win_max']
        froz_min = window['dis_froz_min']
        froz_max = window['dis_froz_max']
        num_wann = self.inputs.wannier_parameters.get_attr('num_wann')

        # max >= min
        if win_min > win_max or froz_min > froz_max:
            return False

        # outer window contains the inner window
        if win_min > froz_min or win_max < froz_max:
            return False

        # check number of bands in inner window <= num_wann
        if np.max(self._count_bands(limits=(froz_min, froz_max))) > num_wann:
            return False
        # check number of bands in outer window >= num_wann
        if np.min(self._count_bands(limits=(win_min, win_max))) < num_wann:
            return False
        return True

    def _count_bands(self, limits):
        lower, upper = sorted(limits)
        bands = self.inputs.wannier_bands.get_bands()
        band_count = np.sum(
            np.logical_and(lower <= bands, bands <= upper),
            axis=-1
        )
        return band_count

    def check_windows(self):
        self.report('Evaluating calculated windows.')
        window_calcs = [self.ctx[key] for key in self.ctx if key.startswith('window_')]
        window_calcs = sorted(window_calcs, key=lambda calc: calc.out.difference.value)
        optimal_calc = window_calcs[0]
        self.out('tb_model', optimal_calc.out.tb_model)
        self.out('difference', optimal_calc.out.difference)
        self.out('window', optimal_calc.inp.window)
        self.report('Finished!')
