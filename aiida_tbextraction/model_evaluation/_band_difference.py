"""
Defines a workflow which evaluates a tight-binding model by comparing its bandstructure to a reference bandstructure.
"""

from fsc.export import export

from aiida.orm import DataFactory, CalculationFactory
from aiida.orm.code import Code
from aiida.orm.data.base import Float
from aiida.work.workchain import ToContext

from aiida_tools import check_workchain_step

from . import ModelEvaluationBase


@export  # pylint: disable=abstract-method
class BandDifferenceModelEvaluation(ModelEvaluationBase):
    """
    Evaluates a tight-binding model by comparing its bandstructure to the reference bandstructure.
    """

    @classmethod
    def define(cls, spec):
        super(BandDifferenceModelEvaluation, cls).define(spec)
        spec.input(
            'bands_inspect_code',
            valid_type=Code,
            help='Code that runs the bands_inspect CLI.'
        )
        spec.output(
            'plot',
            valid_type=DataFactory('singlefile'),
            help='Plot comparing the reference and evaluated bandstructure.'
        )

        spec.outline(
            cls.calculate_bands, cls.calculate_difference_and_plot,
            cls.finalize
        )

    def setup_calc(self, calc_string, code_param):
        """
        Helper function to set up a calculation of a specified type.
        """
        process = CalculationFactory(calc_string).process()
        inputs = process.get_inputs_template()
        inputs.code = self.inputs[code_param]
        inputs._options.resources = {'num_machines': 1}  # pylint: disable=protected-access
        inputs._options.withmpi = False  # pylint: disable=protected-access
        return process, inputs

    @check_workchain_step
    def calculate_bands(self):
        """
        Calculate the bandstructure of the given tight-binding model.
        """
        process, inputs = self.setup_calc(
            'tbmodels.eigenvals', 'tbmodels_code'
        )
        inputs.tb_model = self.inputs.tb_model
        inputs.kpoints = self.inputs.reference_bands
        self.report("Running TBmodels eigenvals calculation.")
        pid = self.submit(process, **inputs)
        return ToContext(calculated_bands=pid)

    @check_workchain_step
    def calculate_difference_and_plot(self):
        """
        Calculate the difference between the tight-binding and reference bandstructures, and plot them.
        """
        process_diff, inputs = self.setup_calc(
            'bands_inspect.difference', 'bands_inspect_code'
        )
        process_plot, _ = self.setup_calc(
            'bands_inspect.plot', 'bands_inspect_code'
        )
        # Inputs for the plot and difference calculations are the same
        inputs.bands1 = self.inputs.reference_bands
        inputs.bands2 = self.ctx.calculated_bands.out.bands
        self.report('Running difference calculation.')
        pid_diff = self.submit(process_diff, **inputs)
        self.report('Running plot calculation.')
        pid_plot = self.submit(process_plot, **inputs)
        return ToContext(difference=pid_diff, plot=pid_plot)

    @check_workchain_step
    def finalize(self):
        """
        Return outputs of the difference and plot calculations.
        """
        self.out('cost_value', Float(self.ctx.difference.out.difference))
        self.out('plot', self.ctx.plot.out.plot)
