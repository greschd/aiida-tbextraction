# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow which optimizes the energy windows.
"""

import copy

import numpy as np
from fsc.export import export

from aiida.orm import load_node
from aiida.orm import List, Float
from aiida.orm import Dict
from aiida.engine import WorkChain, ToContext
from aiida.common.links import LinkType

from aiida_tools import check_workchain_step
from aiida_optimize.engines import NelderMead
from aiida_optimize.workchain import OptimizationWorkChain

from .run_window import RunWindow


@export
class WindowSearch(WorkChain):
    """
    This workchain runs a series of possible energy windows and selects the best-matching tight-binding model.
    """

    @classmethod
    def define(cls, spec):
        super(WindowSearch, cls).define(spec)

        spec.expose_inputs(RunWindow, exclude=['window', 'wannier_kpoints'])
        spec.input(
            'initial_window',
            valid_type=List,
            help=
            'Initial value for the disentanglement energy windows, given as a list ``[dis_win_min, dis_froz_min, dis_froz_max, dis_win_max]``.'
        )
        spec.input(
            'window_tol',
            valid_type=Float,
            default=Float(0.5),
            help='Tolerance in energy windows for the window optimization.'
        )
        spec.input(
            'cost_tol',
            valid_type=Float,
            default=Float(0.02),
            help="Tolerance in the 'cost_value' for the window optimization."
        )

        spec.outline(cls.create_optimization, cls.finalize)

    @check_workchain_step
    def create_optimization(self):
        """
        Run the optimization workchain.
        """
        self.report('Launching Window optimization.')
        initial_window_list = self.inputs.initial_window.get_attr('list')
        window_simplex = [initial_window_list]
        simplex_dist = 0.5
        for i in range(len(initial_window_list)):
            window = copy.deepcopy(initial_window_list)
            window[i] += simplex_dist
            window_simplex.append(window)

        return ToContext(
            optimization=self.submit(
                OptimizationWorkChain,
                engine=NelderMead,
                engine_kwargs=Dict(
                    dict=dict(
                        result_key='cost_value',
                        xtol=self.inputs.window_tol.value,
                        ftol=np.inf,
                        input_key='window',
                        simplex=window_simplex
                    )
                ),
                calculation_workchain=RunWindow,
                calculation_inputs=dict(
                    wannier_kpoints=self.inputs.wannier_bands,
                    **self.exposed_inputs(RunWindow)
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the optimization results to the outputs.
        """
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
