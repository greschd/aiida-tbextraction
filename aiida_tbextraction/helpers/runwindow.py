try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export
from aiida.orm import DataFactory
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext

from ..model_evaluation import ModelEvaluation
from ..tbextraction import TbExtraction
from .._utils import check_workchain_step
from .._workchain_inputs import WORKCHAIN_INPUT_KWARGS


@export
class RunWindow(WorkChain):
    """
    This workchain runs the tight-binding extraction and analysis for a given energy window.
    """

    @classmethod
    def define(cls, spec):
        super(RunWindow, cls).define(spec)
        spec.expose_inputs(TbExtraction)
        spec.expose_inputs(ModelEvaluation, exclude=['tb_model'])
        spec.expose_inputs(
            ModelEvaluation, include=[], namespace='model_evaluation'
        )
        spec.input('window', valid_type=DataFactory('parameter'))
        spec.input('model_evaluation_workflow', **WORKCHAIN_INPUT_KWARGS)

        spec.outline(cls.extract_model, cls.evaluate_bands, cls.finalize)

    @check_workchain_step
    def extract_model(self):
        inputs = self.exposed_inputs(TbExtraction)
        # set the energy window
        wannier_parameters = inputs.pop('wannier_parameters').get_dict()
        wannier_parameters.update(self.inputs.window.get_dict())
        inputs['wannier_parameters'] = DataFactory('parameter')(
            dict=wannier_parameters
        )
        self.report("Extracting tight-binding model.")
        return ToContext(tbextraction_calc=submit(TbExtraction, **inputs))

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
                    self.exposed_inputs(ModelEvaluation),
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        self.report("Adding band difference to output.")
        self.out('cost_value', self.ctx.model_evaluation_wf.out.cost_value)
