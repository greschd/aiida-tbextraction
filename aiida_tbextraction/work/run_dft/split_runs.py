from .base import RunDFTBase

from .._utils import check_workchain_step
from .._workchain_inputs import WORKCHAIN_INPUT_KWARGS
from .reference_bands.base import ReferenceBandsBase
from .wannier_input.base import ToWannier90Base


class SplitDFTRuns(RunDFTBase):
    """
    """

    @classmethod
    def define(cls, spec):
        super(SplitDFTRuns, cls).define(spec)

        spec.input('reference_bands_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('to_wannier90_workflow', **WORKCHAIN_INPUT_KWARGS)

        # Add dynamic namespaces
        spec.expose_inputs(
            ReferenceBandsBase, namespace='reference_bands', include=[]
        )
        spec.expose_inputs(
            ToWannier90Base, namespace='to_wannier90', include=[]
        )

        spec.outline(cls.run_dft, cls.finalize)

    @check_workchain_step
    def run_dft(self):
        return ToContext(
            reference_bands=submit(
                self.get_deserialized_input('reference_bands_workflow'),
                **self.exposed_inputs(
                    ReferenceBandsBase, namespace='reference_bands'
                )
            ),
            to_wannier90=submit(
                self.get_deserialized_input('to_wannier90_workflow'),
                **self.exposed_inputs(
                    ToWannier90Base, namespace='to_wannier90'
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        self.out_many(
            **self.exposed_outputs(
                self.ctx.reference_bands, ReferenceBandsBase
            )
        )
        self.out_many(
            **self.exposed_outputs(self.ctx.to_wannier90, ToWannier90Base)
        )
