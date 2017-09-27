from aiida.work.workchain import WorkChain

from .reference_bands.base import ReferenceBandsBase
from .wannier_input.base import ToWannier90Base


class RunDFTBase(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        super(RunDFTBase, cls).define(spec)

        spec.expose_inputs(ReferenceBandsBase)
        spec.expose_inputs(ToWannier90Base)

        spec.expose_outputs(ReferenceBandsBase)
        spec.expose_outputs(ToWannier90Base)
