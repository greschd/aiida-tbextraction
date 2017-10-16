from fsc.export import export

import aiida
aiida.try_load_dbenv()
from aiida.work.workchain import WorkChain

from .reference_bands import ReferenceBandsBase
from .wannier_input import WannierInputBase


@export
class DFTRunBase(WorkChain):
    """
    """

    @classmethod
    def define(cls, spec):
        super(DFTRunBase, cls).define(spec)

        spec.expose_inputs(ReferenceBandsBase)
        spec.expose_inputs(WannierInputBase)

        spec.expose_outputs(ReferenceBandsBase)
        spec.expose_outputs(WannierInputBase)
