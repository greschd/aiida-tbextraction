"""
Defines the workflow to optimize tight-binding models from DFT inputs with different strain values.
"""

from fsc.export import export

from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext

from aiida_tools import check_workchain_step
from aiida_strain.work import ApplyStrainsWithSymmetry

from .first_principles_tb import FirstPrinciplesTbExtraction


@export  # pylint: disable=abstract-method
class StrainedFpTbExtraction(WorkChain):
    """
    Workflow to optimize a DFT-based tight-binding model for different strain values.
    """

    @classmethod
    def define(cls, spec):
        super(StrainedFpTbExtraction, cls).define(spec)

        spec.expose_inputs(ApplyStrainsWithSymmetry)
        spec.expose_inputs(
            FirstPrinciplesTbExtraction, exclude=('structure', 'symmetries')
        )

        spec.outline(cls.run_strain, cls.run_optimize_dft_tb, cls.finalize)

    @check_workchain_step
    def run_strain(self):
        """
        Apply strain to the initial structure to get the strained structures.
        """
        return ToContext(
            apply_strains=submit(
                ApplyStrainsWithSymmetry,
                **self.exposed_inputs(ApplyStrainsWithSymmetry)
            )
        )

    @check_workchain_step
    def run_optimize_dft_tb(self):
        """
        Run the tight-binding optimization for each strained structure.
        """
        apply_strains_outputs = self.ctx.apply_strains.get_outputs_dict()
        tocontext_kwargs = {}
        for strain in self.inputs.strain_strengths:
            key = 'tbextraction_{}'.format(strain)
            structure_key = 'structure_{}'.format(strain)
            symmetries_key = 'symmetries_{}'.format(strain)
            tocontext_kwargs[key] = submit(
                FirstPrinciplesTbExtraction,
                structure=apply_strains_outputs[structure_key],
                symmetries=apply_strains_outputs[symmetries_key],
                **self.exposed_inputs(FirstPrinciplesTbExtraction)
            )
        return ToContext(**tocontext_kwargs)

    @check_workchain_step
    def finalize(self):
        """
        Retrieve and output results.
        """
        for strain in self.inputs.strain_strengths:
            suffix = '_{}'.format(strain)
            calc = self.ctx['tbextraction' + suffix]
            self.out('tb_model' + suffix, calc.out.tb_model)
            self.out('cost_value' + suffix, calc.out.cost_value)
            self.out('window' + suffix, calc.out.window)
