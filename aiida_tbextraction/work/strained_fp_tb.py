from aiida.work.run import submit
from aiida.work.workchain import WorkChain, ToContext

from aiida_strain.work import ApplyStrainsWithSymmetry

from .first_principles_tb import FirstPrinciplesTbExtraction
from ._utils import check_workchain_step


class StrainedFpTbExtraction(WorkChain):
    """
    """
    @classmethod
    def define(cls, spec):
        super(StrainedFpTbExtraction, cls).define(spec)

        spec.inherit_inputs(ApplyStrainsWithSymmetry)
        spec.inherit_inputs(FirstPrinciplesTbExtraction, exclude=('structure', 'symmetries'))

        spec.outline(
            cls.run_strain,
            cls.run_fp_tb_extraction,
            cls.finalize
        )

    @check_workchain_step
    def run_strain(self):
        return ToContext(apply_strains=submit(
            ApplyStrainsWithSymmetry,
            **self.inherited_inputs(ApplyStrainsWithSymmetry)
        ))

    @check_workchain_step
    def run_fp_tb_extraction(self):
        apply_strains_outputs = self.ctx.apply_strains.get_outputs_dict()
        strain_suffixes = []
        for key in apply_strains_outputs:
            if key.startswith('structure_'):
                split_key = key.split('_')
                if len(split_key) > 2:
                    continue
                _, suffix = split_key
                strain_suffixes.append(suffix)

        tocontext_kwargs = {}
        for suffix in strain_suffixes:
            key = 'tbextraction_' + suffix
            structure_key = 'structure_' + suffix
            symmetries_key = 'symmetries_' + suffix
            tocontext_kwargs[key] = submit(
                FirstPrinciplesTbExtraction,
                structure=apply_strains_outputs[structure_key],
                symmetries=apply_strains_outputs[symmetries_key],
                **self.inherited_inputs(FirstPrinciplesTbExtraction)
            )
        return ToContext(**tocontext_kwargs)

    @check_workchain_step
    def finalize(self):
        for key, calc in self.ctx._get_dict().items():
            if key.startswith('tbextraction_'):
                suffix = key.split('_', 1)[1]
                self.out('tb_model_' + suffix, calc.out.tb_model)
                self.out('difference_'  + suffix, calc.out.difference)
                self.out('window_' + suffix, calc.out.window)
