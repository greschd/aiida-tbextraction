import itertools

import numpy as np
from fsc.export import export

from aiida.orm import DataFactory, load_node
from aiida.orm.data.parameter import ParameterData
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext
from aiida.common.links import LinkType

from aiida_tools import check_workchain_step
from aiida_optimize.engines import ParameterSweep
from aiida_optimize.workchain import OptimizationWorkChain

from .runwindow import RunWindow


@export  # pylint: disable=abstract-method
class WindowSearch(WorkChain):
    """
    This workchain runs a series of possible energy windows and selects the best-matching tight-binding model.
    """

    @classmethod
    def define(cls, spec):
        super(WindowSearch, cls).define(spec)

        spec.expose_inputs(RunWindow, exclude=['window', 'wannier_kpoints'])
        spec.input('window_values', valid_type=ParameterData)
        spec.input('wannier_bands', valid_type=DataFactory('array.bands'))

        # TODO: Generalize to allow iterative window search
        spec.outline(cls.create_optimization, cls.finalize)

    @check_workchain_step
    def create_optimization(self):
        valid_windows = self._get_valid_windows()
        if not valid_windows:
            self.report('No valid energy windows found, aborting.')
            raise AssertionError
        else:
            self.report(
                'Found {} valid window configurations.'.format(
                    len(valid_windows)
                )
            )
        return ToContext(
            optimization=submit(
                OptimizationWorkChain,
                engine=ParameterSweep,
                engine_kwargs=ParameterData(
                    dict=dict(
                        result_key='cost_value', parameters=valid_windows
                    )
                ),
                calculation_workchain=RunWindow,
                calculation_inputs=dict(
                    wannier_kpoints=self.inputs.wannier_bands,
                    **self.exposed_inputs(RunWindow)
                )
            )
        )

    def _get_valid_windows(self):
        window_values = self.inputs.window_values.get_dict()
        all_windows = [{
            key: val
            for key, val in zip(window_values.keys(), window_choice)
        } for window_choice in itertools.product(*window_values.values())]
        return [{
            'window': window
        } for window in all_windows if self._window_is_valid(window)]

    def _window_is_valid(self, window):
        win_min = window['dis_win_min']
        win_max = window['dis_win_max']
        froz_min = window['dis_froz_min']
        froz_max = window['dis_froz_max']
        num_wann = int(self.inputs.wannier_parameters.get_attr('num_wann'))

        window_invalid_str = 'Window [{}, ({}, {}), {}] is invalid'.format(
            win_min, froz_min, froz_max, win_max
        )
        # max >= min
        if win_min > win_max or froz_min > froz_max:
            self.report('{}: max < min.'.format(window_invalid_str))
            return False

        # outer window contains the inner window
        if win_min > froz_min or win_max < froz_max:
            self.report(
                '{}: Outer window does not contain inner.'.
                format(window_invalid_str)
            )
            return False

        # check number of bands in inner window <= num_wann
        if np.max(self._count_bands(limits=(froz_min, froz_max))) > num_wann:
            self.report(
                '{}: Too many bands in inner window.'.
                format(window_invalid_str)
            )
            return False
        # check number of bands in outer window >= num_wann
        if np.min(self._count_bands(limits=(win_min, win_max))) < num_wann:
            self.report(
                '{}: Too few bands in outer window.'.
                format(window_invalid_str)
            )
            return False
        return True

    def _count_bands(self, limits):
        lower, upper = sorted(limits)
        bands = self.inputs.wannier_bands.get_bands()
        band_count = np.sum(
            np.logical_and(lower <= bands, bands <= upper), axis=-1
        )
        return band_count

    @check_workchain_step
    def finalize(self):
        self.report('Add optimization results to outputs.')
        optimal_calc = load_node(
            self.ctx.optimization.out.calculation_uuid.value
        )
        self.report('Adding optimal window to outputs.')
        self.out('window', optimal_calc.inp.window)
        for label, node in optimal_calc.get_outputs(
            also_labels=True, link_type=LinkType.RETURN
        ):
            self.report("Adding {} to outputs.".format(label))
            self.out(label, node)
        self.report('Finished!')
