from aiida.orm import CalculationFactory
from aiida.orm.code import Code
from aiida.orm.data.base import Float
from aiida.work import submit
from aiida.work.workchain import ToContext

from .base import ModelEvaluation
from .._utils import check_workchain_step

class BandDifferenceModelEvaluation(ModelEvaluation):
    @classmethod
    def define(cls, spec):
        super(BandDifferenceModelEvaluation, cls).define(spec)
        spec.input('bands_inspect_code', valid_type=Code)

        spec.outline(
            cls.calculate_bands, cls.calculate_difference, cls.finalize
        )

    def setup_calc(self, calc_string, code_param):
        process = CalculationFactory(calc_string).process()
        inputs = process.get_inputs_template()
        inputs.code = self.inputs[code_param]
        inputs._options.resources = {'num_machines': 1}
        inputs._options.withmpi = False
        return process, inputs

    @check_workchain_step
    def calculate_bands(self):
        process, inputs = self.setup_calc('tbmodels.eigenvals', 'tbmodels_code')
        inputs.tb_model = self.inputs.tb_model
        inputs.kpoints = self.inputs.reference_bands
        self.report("Running TBmodels eigenvals calculation.")
        pid = submit(process, **inputs)
        return ToContext(calculated_bands=pid)

    @check_workchain_step
    def calculate_difference(self):
        process, inputs = self.setup_calc('bands_inspect.difference', 'bands_inspect_code')
        inputs.bands1 = self.inputs.reference_bands
        inputs.bands2 = self.ctx.calculated_bands.out.bands
        self.report('Running difference calculation.')
        pid = submit(process, **inputs)
        return ToContext(difference=pid)

    @check_workchain_step
    def finalize(self):
        self.out('cost_value', Float(self.ctx.difference.out.difference))
