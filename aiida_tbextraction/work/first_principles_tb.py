try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

import plum.util
from aiida.orm.data.base import Str
from aiida.work.workchain import WorkChain

from .windowsearch import WindowSearch
from .reference_bands.base import ReferenceBandsBase
from .wannier_input.base import ToWannier90Base

@singledispatch
def _get_fullname(cls_obj):
    return Str(plum.util.fullname(cls_obj))

@_get_fullname.register(str)
def _(cls_name):
    return Str(cls_name)

@_get_fullname.register(Str)
def _(cls_name):
    return cls_name

def _load_class(cls_name):
    return plum.util.load_class(cls_name.value)

WORKCHAIN_INPUT_KWARGS = {
    'valid_type': Str,
    'serialize_fct': _get_fullname,
    'deserialize_fct': _load_class
}

class FirstPrinciplesTbExtraction(WorkChain):
    """
    Creates a tight-binding model by first running first-principles calculations to get a reference bandstructure and Wannier90 input, and then optimizing the energy window to get an optimized symmetric tight-binding model.
    """
    @classmethod
    def define(cls, spec):
        super(FirstPrinciplesTbExtraction, cls).define(spec)

        # TODO: Scope inherited inputs
        spec.inherit_inputs(WindowSearch)
        spec.inherit_inputs(ReferenceBandsBase)
        spec.inherit_inputs(ToWannier90Base)

        spec.input('reference_bands_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('to_wannier90_workflow', **WORKCHAIN_INPUT_KWARGS)

        spec.outline(
            cls.run_dft,
            cls.run_windowsearch,
            cls.finalize
        )

    def run_dft(self):
        pass

    def run_windowsearch(self):
        pass

    def finalize(self):
        pass
