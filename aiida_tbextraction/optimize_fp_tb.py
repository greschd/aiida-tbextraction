"""
Defines the workflow that runs first-principles calculations and creates an optimized tight-binding model.
"""

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.orm.data.base import List
from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline
from aiida.work.workchain import WorkChain, ToContext
from aiida.work.class_loader import CLASS_LOADER
from aiida.common.links import LinkType

from aiida_tools import check_workchain_step
from aiida_tools.workchain_inputs import WORKCHAIN_INPUT_KWARGS

from .energy_windows.windowsearch import WindowSearch
from .fp_run import FirstPrinciplesRunBase


@export
class OptimizeFirstPrinciplesTightBinding(WorkChain):
    """
    Creates a tight-binding model by first running first-principles calculations to get a reference bandstructure and Wannier90 input, and then optimizing the energy window to get an optimized symmetric tight-binding model.
    """

    @classmethod
    def define(cls, spec):
        super(OptimizeFirstPrinciplesTightBinding, cls).define(spec)

        # inputs which are inherited at the top level
        spec.expose_inputs(FirstPrinciplesRunBase, exclude=())
        # create namespace for additional inputs
        spec.input_namespace('fp_run', dynamic=True)

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

        spec.input('fp_run_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('slice_reference_bands', valid_type=List, required=False)
        spec.input('slice_tb_model', valid_type=List, required=False)

        spec.expose_outputs(WindowSearch)

        spec.outline(cls.fp_run, cls.run_windowsearch, cls.finalize)

    @check_workchain_step
    def fp_run(self):
        """
        Runs the first-principles calculation workflow.
        """
        self.report("Starting DFT workflows.")
        return ToContext(
            fp_run=self.submit(
                CLASS_LOADER.load_class(self.inputs.fp_run_workflow.value),
                **ChainMap(
                    self.inputs.fp_run,
                    self.
                    exposed_inputs(FirstPrinciplesRunBase, namespace='fp_run'),
                )
            )
        )

    @check_workchain_step
    def run_windowsearch(self):
        """
        Runs the workflow which creates the optimized tight-binding model.
        """
        # check for wannier_settings from wannier_input workflow
        inputs = self.exposed_inputs(WindowSearch)
        self.report(
            "Merging 'wannier_settings' from input and wannier_input workflow."
        )
        wannier_settings_explicit = inputs.pop(
            'wannier_settings', ParameterData()
        )
        wannier_settings_from_wf = self.ctx.fp_run.get_outputs_dict().get(
            'wannier_settings', ParameterData()
        )
        wannier_settings = merge_parameterdata_inline(
            param_primary=wannier_settings_explicit,
            param_secondary=wannier_settings_from_wf
        )[1]['result']

        # prefer wannier_projections from wannier_input workflow if it exists
        wannier_projections = self.ctx.fp_run.get_outputs_dict().get(
            'wannier_projections', inputs.pop('wannier_projections', None)
        )

        # slice reference bands if necessary
        reference_bands = self.ctx.fp_run.out.bands
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
            windowsearch=self.submit(
                WindowSearch,
                reference_bands=reference_bands,
                wannier_bands=self.ctx.fp_run.out.wannier_bands,
                wannier_parameters=self.ctx.fp_run.out.wannier_parameters,
                wannier_input_folder=self.ctx.fp_run.out.wannier_input_folder,
                wannier_settings=wannier_settings,
                wannier_projections=wannier_projections,
                **inputs
            )
        )

    @check_workchain_step
    def finalize(self):
        self.report("Adding outputs from WindowSearch workflow.")
        windowsearch = self.ctx.windowsearch
        for label, node in windowsearch.get_outputs(
            also_labels=True, link_type=LinkType.RETURN
        ):
            self.out(label, node)


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
