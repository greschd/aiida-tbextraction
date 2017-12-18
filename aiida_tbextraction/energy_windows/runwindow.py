try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

import numpy as np
from fsc.export import export

from aiida.orm import DataFactory
from aiida.orm.data.base import List, Float
from aiida.orm.calculation.inline import make_inline
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext, if_
from aiida.common.links import LinkType

from aiida_tools import check_workchain_step
from aiida_tools.workchain_inputs import WORKCHAIN_INPUT_KWARGS

from ..model_evaluation import ModelEvaluationBase
from ..calculate_tb import TightBindingCalculation


@export  # pylint: disable=abstract-method
class RunWindow(WorkChain):
    """
    This workchain runs the tight-binding extraction and analysis for a given energy window.
    """

    @classmethod
    def define(cls, spec):
        super(RunWindow, cls).define(spec)
        spec.expose_inputs(TightBindingCalculation)
        spec.expose_inputs(ModelEvaluationBase, exclude=['tb_model'])
        spec.expose_inputs(
            ModelEvaluationBase, include=[], namespace='model_evaluation'
        )
        spec.input('window', valid_type=List)
        spec.input('wannier_bands', valid_type=DataFactory('array.bands'))
        spec.input('model_evaluation_workflow', **WORKCHAIN_INPUT_KWARGS)

        spec.expose_outputs(ModelEvaluationBase)
        spec.outline(
            if_(cls.window_valid)(
                cls.calculate_model, cls.evaluate_bands, cls.finalize
            ),
            if_(cls.window_invalid)(cls.abort_invalid)
        )

    def window_invalid(self):
        return not self.window_valid()

    def window_valid(self):
        window_list = self.inputs.window.get_attr('list')
        win_min, froz_min, froz_max, win_max = window_list
        num_wann = int(self.inputs.wannier_parameters.get_attr('num_wann'))

        window_invalid_str = 'Window [{}, ({}, {}), {}] is invalid'.format(
            *window_list
        )

        # window values must be sorted
        if sorted(window_list) != window_list:
            self.report(
                '{}: windows values not sorted.'.format(window_invalid_str)
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
    def calculate_model(self):
        inputs = self.exposed_inputs(TightBindingCalculation)
        # set the energy window
        inputs.update(
            add_window_parameters_inline(
                wannier_parameters=inputs.pop('wannier_parameters'),
                window=self.inputs.window
            )[1]
        )
        self.report("Calculating tight-binding model.")
        return ToContext(
            tbextraction_calc=submit(TightBindingCalculation, **inputs)
        )

    @check_workchain_step
    def evaluate_bands(self):
        tb_model = self.ctx.tbextraction_calc.out.tb_model
        self.report("Adding tight-binding model to output.")
        self.out('tb_model', tb_model)
        self.report("Running model evaluation.")
        return ToContext(
            model_evaluation_wf=submit(
                self.get_deserialized_input('model_evaluation_workflow'),
                tb_model=tb_model,
                **ChainMap(
                    self.inputs.model_evaluation,
                    self.exposed_inputs(ModelEvaluationBase),
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        for label, node in self.ctx.model_evaluation_wf.get_outputs(
            also_labels=True, link_type=LinkType.RETURN
        ):
            self.report("Adding {} to outputs.".format(label))
            self.out(label, node)

    @check_workchain_step
    def abort_invalid(self):
        self.report('Window is invalid, assigning infinite cost_value.')
        self.out('cost_value', Float('inf'))


@make_inline
def add_window_parameters_inline(wannier_parameters, window):
    param_dict = wannier_parameters.get_dict()
    win_min, froz_min, froz_max, win_max = window.get_attr('list')
    param_dict.update(
        dict(
            dis_win_min=win_min,
            dis_win_max=win_max,
            dis_froz_min=froz_min,
            dis_froz_max=froz_max,
        )
    )
    return {'wannier_parameters': DataFactory('parameter')(dict=param_dict)}
