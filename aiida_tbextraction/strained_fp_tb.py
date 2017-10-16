from fsc.export import export

import aiida
aiida.try_load_dbenv()
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext

from aiida_strain.work import ApplyStrainsWithSymmetry

from .first_principles_tb import FirstPrinciplesTbExtraction
from ._utils import check_workchain_step


@export
class StrainedFpTbExtraction(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        super(StrainedFpTbExtraction, cls).define(spec)

        spec.expose_inputs(ApplyStrainsWithSymmetry)
        spec.expose_inputs(
            FirstPrinciplesTbExtraction, exclude=('structure', 'symmetries')
        )

        spec.outline(cls.run_strain, cls.run_fp_tb_extraction, cls.finalize)

    @check_workchain_step
    def run_strain(self):
        return ToContext(
            apply_strains=submit(
                ApplyStrainsWithSymmetry,
                **self.exposed_inputs(ApplyStrainsWithSymmetry)
            )
        )

    @check_workchain_step
    def run_fp_tb_extraction(self):
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
        for strain in self.inputs.strain_strengths:
            suffix = '_{}'.format(strain)
            calc = self.ctx['tbextraction' + suffix]
            self.out('tb_model' + suffix, calc.out.tb_model)
            self.out('cost_value' + suffix, calc.out.cost_value)
            self.out('window' + suffix, calc.out.window)
