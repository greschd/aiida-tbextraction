try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

import plum.util
from aiida.work.run import submit
from aiida.orm.data.base import Str
from aiida.work.workchain import WorkChain, ToContext

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

        # inputs which are inherited at the top level
        spec.inherit_inputs(
            ReferenceBandsBase,
            exclude=(
                'code',
                'parameters',
                'calculation_kwargs',
            )
        )
        # inputs which are inherited at the namespace level
        spec.inherit_inputs(
            ReferenceBandsBase,
            namespace='reference_bands',
            exclude=(
                'structure',
                'potentials',
                'kpoints',
                'kpoints_mesh',
            )
        )

        # Inputs which are inherited at the top level
        spec.inherit_inputs(
            ToWannier90Base,
            exclude=(
                'code',
                'parameters',
                'calculation_kwargs',
            )
        )
        # inputs which are inherited at the namespace level
        spec.inherit_inputs(
            ToWannier90Base,
            namespace='to_wannier90'
            exclude=(
                'code',
                'structure',
                'potentials',
                'kpoints_mesh',
                'wannier_projections',
                'wannier_parameters',
            )
        )

        spec.inherit_inputs(
            WindowSearch,
            namespace='window_search',
            exclude=(
                'wannier_input_folder',
                'reference_bands'
            )
        )

        spec.input('reference_bands_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('to_wannier90_workflow', **WORKCHAIN_INPUT_KWARGS)

        spec.outline(
            cls.run_dft,
            cls.run_windowsearch,
            cls.finalize
        )

    def run_dft(self):
        reference_bands_pid = submit(
            self.get_deserialized_input('reference_bands_workflow'),
            **self.inherited_inputs(ReferenceBandsBase)
        )
        to_wannier90_pid = submit(
            self.get_deserialized_input('to_wannier90_workflow'),
            code=self.inputs.wannier_code,
            **self.inherited_inputs(ToWannier90Base)
        )
        return ToContext(
            reference_bands=reference_bands_pid,
            to_wannier90=to_wannier90_pid
        )

    def run_windowsearch(self):
        return ToContext(windowsearch=submit(
            WindowSearch,
            wannier_input_folder=self.ctx.to_wannier90.out.wannier_input_folder,
            reference_bands=self.ctx.reference_bands.out.bands,
            **self.inherited_inputs(WindowSearch)
        ))

    def finalize(self):
        window_wf = self.ctx.windowsearch
        self.out('tb_model', window_wf.out.tb_model)
        self.out('difference', window_wf.out.difference)
        self.out('window', window_wf.out.window)
