try:
    from functools import singledispatch
    from collections import ChainMap
except ImportError:
    from singledispatch import singledispatch
    from chainmap import ChainMap

from aiida.work.run import submit
from aiida.orm.data.base import List
from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline
from aiida.work.workchain import WorkChain, ToContext

from .windowsearch import WindowSearch
from .run_dft import RunDFTBase
# from .reference_bands import ReferenceBandsBase
# from .wannier_input import WannierInputBase
from ._utils import check_workchain_step
from ._workchain_inputs import WORKCHAIN_INPUT_KWARGS


class FirstPrinciplesTbExtraction(WorkChain):
    """
    Creates a tight-binding model by first running first-principles calculations to get a reference bandstructure and Wannier90 input, and then optimizing the energy window to get an optimized symmetric tight-binding model.
    """

    @classmethod
    def define(cls, spec):
        super(FirstPrinciplesTbExtraction, cls).define(spec)

        # inputs which are inherited at the top level
        spec.expose_inputs(
            RunDFTBase, exclude=(
                'code',
                'parameters',
                'calculation_kwargs',
            )
        )
        # inputs which are inherited at the namespace level
        spec.expose_inputs(
            RunDFTBase,
            namespace='run_dft',
            include=(
                'code',
                'parameters',
                'calculation_kwargs',
            )
        )

        # top-level scope
        spec.expose_inputs(
            WindowSearch,
            exclude=(
                'wannier_bands',
                'reference_bands',
                'wannier_parameters',
                'wannier_input_folder',
                'slice_idx',
            )
        )

        spec.input('run_dft_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('slice_reference_bands', valid_type=List, required=False)
        spec.input('slice_tb_model', valid_type=List, required=False)

        spec.outline(cls.run_dft, cls.run_windowsearch, cls.finalize)

    @check_workchain_step
    def run_dft(self):
        self.report("Starting DFT workflows.")
        return ToContext(
            run_dft=submit(
                self.get_deserialized_input('run_dft_workflow'),
                **self.exposed_inputs(ReferenceBandsBase, namespace='run_dft')
            )
        )

    @check_workchain_step
    def run_windowsearch(self):
        # check for wannier_settings from to_wannier90 workflow
        inputs = self.exposed_inputs(WindowSearch)
        self.report(
            "Merging 'wannier_settings' from input and to_wannier90 workflow."
        )
        wannier_settings_explicit = inputs.pop(
            'wannier_settings', ParameterData()
        )
        wannier_settings_from_wf = self.ctx.run_dft.get_outputs_dict().get(
            'wannier_settings', ParameterData()
        )
        wannier_settings = merge_parameterdata_inline(
            param_primary=wannier_settings_explicit,
            param_secondary=wannier_settings_from_wf
        )[1]['result']

        # prefer wannier_projections from to_wannier90 workflow if it exists
        wannier_projections = self.ctx.run_dft.get_outputs_dict().get(
            'wannier_projections', inputs.pop('wannier_projections', None)
        )

        # slice reference bands if necessary
        reference_bands = self.ctx.run_dft.out.bands
        slice_reference_bands = self.inputs.get('slice_reference_bands', None)
        if slice_reference_bands is not None:
            reference_bands = slice_bands_inline(
                bands=reference_bands, slice_idx=slice_reference_bands
            )[1]['result']

        # get slice_idx for windowsearch
        slice_idx = self.inputs.get('slice_tb_model', None)
        if slice_idx is not None:
            inputs['slice_idx'] = slice_idx

        self.report("Starting WindowSearch workflow.")
        return ToContext(
            windowsearch=submit(
                WindowSearch,
                reference_bands=reference_bands,
                wannier_bands=self.ctx.to_wannier90.out.wannier_bands,
                wannier_parameters=self.ctx.to_wannier90.out.
                wannier_parameters,
                wannier_input_folder=self.ctx.to_wannier90.out.
                wannier_input_folder,
                wannier_settings=wannier_settings,
                wannier_projections=wannier_projections,
                **inputs
            )
        )

    @check_workchain_step
    def finalize(self):
        self.report("Adding outputs from WindowSearch workflow.")
        windowsearch = self.ctx.windowsearch
        self.out('tb_model', windowsearch.out.tb_model)
        self.out('cost_value', windowsearch.out.cost_value)
        self.out('window', windowsearch.out.window)


@make_inline
def merge_parameterdata_inline(param_primary, param_secondary):
    return {
        'result':
        ParameterData(
            dict=ChainMap(
                param_primary.get_dict(), param_secondary.get_dict()
            )
        )
    }


@make_inline
def slice_bands_inline(bands, slice_idx):
    result = bands.copy()
    result.set_bands(result.get_bands()[:, slice_idx.get_attr('list')])
    return {'result': result}
