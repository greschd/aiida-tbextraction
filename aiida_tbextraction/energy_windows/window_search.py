# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow which optimizes the energy windows.
"""

import copy

from aiida import orm
from aiida.engine import WorkChain, ToContext

from aiida_tools import check_workchain_step, get_outputs_dict
from aiida_optimize import OptimizationWorkChain
from aiida_optimize.engines import NelderMead

from .run_window import RunWindow

__all__ = ('WindowSearch', )


class WindowSearch(WorkChain):
    """
    This workchain runs a series of possible energy windows and selects the best-matching tight-binding model.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(RunWindow, exclude=['window', 'wannier.kpoints'])
        # Workaround for plumpy issue #135 (https://github.com/aiidateam/plumpy/issues/135)
        spec.inputs['model_evaluation'].dynamic = True
        spec.input(
            'initial_window',
            valid_type=orm.List,
            help=
            'Initial value for the disentanglement energy windows, given as a list ``[dis_win_min, dis_froz_min, dis_froz_max, dis_win_max]``.'
        )
        spec.input(
            'window_tol',
            valid_type=orm.Float,
            default=lambda: orm.Float(0.5),
            help='Tolerance in energy windows for the window optimization.'
        )
        spec.input(
            'cost_tol',
            valid_type=orm.Float,
            default=lambda: orm.Float(0.02),
            help="Tolerance in the 'cost_value' for the window optimization."
        )

        spec.output('window', valid_type=orm.List)
        spec.outputs.dynamic = True
        spec.outline(cls.create_optimization, cls.finalize)

    @check_workchain_step
    def create_optimization(self):
        """
        Run the optimization workchain.
        """
        self.report('Launching Window optimization.')
        initial_window_list = self.inputs.initial_window.get_list()
        window_simplex = [initial_window_list]
        simplex_dist = 0.5
        for i in range(len(initial_window_list)):
            window = copy.deepcopy(initial_window_list)
            window[i] += simplex_dist
            window_simplex.append(window)

        runwindow_inputs = self.exposed_inputs(RunWindow)
        runwindow_inputs['wannier']['kpoints'] = self.inputs.wannier_bands
        return ToContext(
            optimization=self.submit(
                OptimizationWorkChain,
                engine=NelderMead,
                engine_kwargs=orm.Dict(
                    dict=dict(
                        result_key='cost_value',
                        xtol=self.inputs.window_tol.value,
                        ftol=None,
                        input_key='window',
                        simplex=window_simplex
                    )
                ),
                evaluate_process=RunWindow,
                evaluate=runwindow_inputs
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the optimization results to the outputs.
        """
        self.report('Add optimization results to outputs.')
        optimal_calc = orm.load_node(
            self.ctx.optimization.outputs.optimal_process_uuid.value
        )
        self.report('Adding optimal window to outputs.')
        self.out('window', optimal_calc.inputs.window)
        self.report("Adding outputs of the optimal calculation.")
        self.out_many(get_outputs_dict(optimal_calc))
        self.report('Finished!')
