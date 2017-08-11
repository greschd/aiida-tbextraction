try:
    from functools import singledispatch
    from collections import ChainMap
except ImportError:
    from singledispatch import singledispatch
    from chainmap import ChainMap

import plum.util
from aiida.work.run import submit
from aiida.orm.data.base import Str, List
from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline
from aiida.work.workchain import WorkChain, ToContext

from .windowsearch import WindowSearch
from .reference_bands.base import ReferenceBandsBase
from .wannier_input.base import ToWannier90Base
from ._utils import check_workchain_step

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
            namespace='to_wannier90',
            exclude=(
                'structure',
                'potentials',
                'kpoints_mesh',
                'wannier_projections',
                'wannier_parameters',
            )
        )

        # top-level scope
        spec.inherit_inputs(
            WindowSearch,
            exclude=(
                'wannier_bands',
                'reference_bands',
                'wannier_kpoints',
                'wannier_parameters',
                'wannier_input_folder',
                'slice_idx',
            )
        )

        spec.input('reference_bands_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('to_wannier90_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('slice_reference_bands', valid_type=List, required=False)
        spec.input('slice_tb_model', valid_type=List, required=False)

        spec.outline(
            cls.run_dft,
            cls.run_windowsearch,
            cls.finalize
        )

    @check_workchain_step
    def run_dft(self):
        self.report("Starting DFT workflows.")
        reference_bands_pid = submit(
            self.get_deserialized_input('reference_bands_workflow'),
            **self.inherited_inputs(ReferenceBandsBase)
        )
        to_wannier90_pid = submit(
            self.get_deserialized_input('to_wannier90_workflow'),
            **self.inherited_inputs(ToWannier90Base)
        )
        return ToContext(
            reference_bands=reference_bands_pid,
            to_wannier90=to_wannier90_pid
        )

    @check_workchain_step
    def run_windowsearch(self):
        # check for wannier_settings from to_wannier90 workflow
        inputs = self.inherited_inputs(WindowSearch)
        self.report("Merging 'wannier_settings' from input and to_wannier90 workflow.")
        wannier_settings_explicit = inputs.pop(
            'wannier_settings', ParameterData()
        )
        wannier_settings_from_wf = self.ctx.to_wannier90.get_outputs_dict().get(
            'wannier_settings', ParameterData()
        )
        wannier_settings = merge_parameterdata_inline(
            param_primary=wannier_settings_explicit,
            param_secondary=wannier_settings_from_wf
        )[1]['result']

        # prefer wannier_projections from to_wannier90 workflow if it exists
        wannier_projections = self.ctx.to_wannier90.get_outputs_dict().get(
            'wannier_projections',
            inputs.pop('wannier_projections', None)
        )

        # slice reference bands if necessary
        reference_bands = self.ctx.reference_bands.out.bands
        slice_reference_bands = self.inputs.get('slice_reference_bands', None)
        if slice_reference_bands is not None:
            reference_bands = slice_bands_inline(
                bands=reference_bands,
                slice_idx=slice_reference_bands
            )[1]['result']

        # get slice_idx for windowsearch
        slice_idx = self.inputs.get('slice_tb_model', None)
        if slice_idx is not None:
            inputs['slice_idx'] = slice_idx

        self.report("Starting WindowSearch workflow.")
        return ToContext(windowsearch=submit(
            WindowSearch,
            reference_bands=reference_bands,
            wannier_bands=self.ctx.to_wannier90.out.wannier_bands,
            wannier_parameters=self.ctx.to_wannier90.out.wannier_parameters,
            wannier_input_folder=self.ctx.to_wannier90.out.wannier_input_folder,
            wannier_settings=wannier_settings,
            wannier_projections=wannier_projections,
            **inputs
        ))

    @check_workchain_step
    def finalize(self):
        self.report("Adding outputs from WindowSearch workflow.")
        windowsearch = self.ctx.windowsearch
        self.out('tb_model', windowsearch.out.tb_model)
        self.out('difference', windowsearch.out.difference)
        self.out('window', windowsearch.out.window)

@make_inline
def merge_parameterdata_inline(param_primary, param_secondary):
    return {'result': ParameterData(dict=ChainMap(
        param_primary.get_dict(), param_secondary.get_dict()
    ))}

@make_inline
def slice_bands_inline(bands, slice_idx):
    result = bands.copy()
    result.set_bands(
        result.get_bands()[:, slice_idx.get_attr('list')]
    )
    return {
        'result': result
    }
