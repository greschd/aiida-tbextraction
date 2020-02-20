# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow which evaluates a tight-binding model by comparing its bandstructure to a reference bandstructure.
"""

from aiida import orm
from aiida.engine import ToContext
from aiida.plugins import CalculationFactory

from aiida_tools import check_workchain_step

from ._base import ModelEvaluationBase

__all__ = ('BandDifferenceModelEvaluation', )


class BandDifferenceModelEvaluation(ModelEvaluationBase):
    """
    Evaluates a tight-binding model by comparing its bandstructure to the reference bandstructure.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input(
            'code_bands_inspect',
            valid_type=orm.Code,
            help='Code that runs the bands_inspect CLI.'
        )
        spec.output(
            'plot',
            valid_type=orm.SinglefileData,
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
        builder = CalculationFactory(calc_string).get_builder()
        builder.code = self.inputs[code_param]
        builder.metadata.options = dict(
            resources={'num_machines': 1}, withmpi=False
        )
        return builder

    @check_workchain_step
    def calculate_bands(self):
        """
        Calculate the bandstructure of the given tight-binding model.
        """
        builder = self.setup_calc('tbmodels.eigenvals', 'code_tbmodels')
        builder.tb_model = self.inputs.tb_model
        builder.kpoints = self.inputs.reference_bands
        self.report("Running TBmodels eigenvals calculation.")
        return ToContext(calculated_bands=self.submit(builder))

    @check_workchain_step
    def calculate_difference_and_plot(self):
        """
        Calculate the difference between the tight-binding and reference bandstructures, and plot them.
        """
        diff_builder = self.setup_calc(
            'bands_inspect.difference', 'code_bands_inspect'
        )
        plot_builder = self.setup_calc(
            'bands_inspect.plot', 'code_bands_inspect'
        )
        # Inputs for the plot and difference calculations are the same
        diff_builder.bands1 = self.inputs.reference_bands
        diff_builder.bands2 = self.ctx.calculated_bands.outputs.bands
        plot_builder.bands1 = self.inputs.reference_bands
        plot_builder.bands2 = self.ctx.calculated_bands.outputs.bands

        self.report('Running difference and plot calculations.')
        self.report('Running plot calculation.')
        return ToContext(
            difference=self.submit(diff_builder),
            plot=self.submit(plot_builder)
        )

    @check_workchain_step
    def finalize(self):
        """
        Return outputs of the difference and plot calculations.
        """
        self.out('cost_value', self.ctx.difference.outputs.difference)
        self.out('plot', self.ctx.plot.outputs.plot)
