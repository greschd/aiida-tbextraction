# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the workflow that runs first-principles calculations and creates an optimized tight-binding model.
"""

from collections import ChainMap

from fsc.export import export

from aiida.orm import List
from aiida.orm import Dict
from aiida.engine import WorkChain, ToContext
from aiida.common.links import LinkType

from aiida_tools import check_workchain_step
from aiida_tools.process_inputs import PROCESS_INPUT_KWARGS, load_object

from .energy_windows.window_search import WindowSearch
from .fp_run import FirstPrinciplesRunBase
from ._calcfunctions import merge_parameterdata_inline, slice_bands_inline
from .energy_windows.auto_guess import get_initial_window_inline


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
        spec.input_namespace(
            'fp_run',
            dynamic=True,
            help='Inputs passed to the ``fp_run_workflow``'
        )

        # top-level scope
        spec.expose_inputs(
            WindowSearch,
            exclude=(
                'initial_window',
                'wannier_bands',
                'reference_bands',
                'wannier_parameters',
                'wannier_input_folder',
                'slice_idx',
            )
        )
        # initial window is not required because it can be guessed.
        spec.input(
            'initial_window',
            valid_type=List,
            help=
            'Initial value for the disentanglement energy windows, given as a list ``[dis_win_min, dis_froz_min, dis_froz_max, dis_win_max]``.',
            required=False
        )

        spec.input(
            'fp_run_workflow',
            help='Workflow which executes the first-principles calculations',
            **PROCESS_INPUT_KWARGS
        )
        spec.input(
            'slice_reference_bands',
            valid_type=List,
            required=False,
            help=
            'Indices for the reference bands which should be included in the model evaluation.'
        )
        spec.input(
            'slice_tb_model',
            valid_type=List,
            required=False,
            help='Indices for slicing (re-ordering) the tight-binding model.'
        )

        spec.expose_outputs(WindowSearch)

        spec.outline(cls.fp_run, cls.run_window_search, cls.finalize)

    @check_workchain_step
    def fp_run(self):
        """
        Runs the first-principles calculation workflow.
        """
        self.report("Starting DFT workflows.")
        return ToContext(
            fp_run=self.submit(
                load_object(self.inputs.fp_run_workflow),
                **ChainMap(
                    self.inputs.fp_run,
                    self.
                    exposed_inputs(FirstPrinciplesRunBase, namespace='fp_run'),
                )
            )
        )

    @check_workchain_step
    def run_window_search(self):
        """
        Runs the workflow which creates the optimized tight-binding model.
        """
        # check for wannier_settings from wannier_input workflow
        inputs = self.exposed_inputs(WindowSearch)
        self.report(
            "Merging 'wannier_settings' from input and wannier_input workflow."
        )
        wannier_settings_explicit = inputs.pop('wannier_settings', Dict())
        wannier_settings_from_wf = self.ctx.fp_run.get_outputs_dict().get(
            'wannier_settings', Dict()
        )
        wannier_settings = merge_parameterdata_inline(
            param_primary=wannier_settings_explicit,
            param_secondary=wannier_settings_from_wf
        )[1]

        # prefer wannier_projections from wannier_input workflow if it exists
        wannier_projections = self.ctx.fp_run.get_outputs_dict().get(
            'wannier_projections', inputs.pop('wannier_projections', None)
        )

        # slice reference bands if necessary
        reference_bands = self.ctx.fp_run.outputs.bands
        slice_reference_bands = self.inputs.get('slice_reference_bands', None)
        if slice_reference_bands is not None:
            reference_bands = slice_bands_inline(
                bands=reference_bands, slice_idx=slice_reference_bands
            )[1]

        # get slice_idx for window_search
        slice_idx = self.inputs.get('slice_tb_model', None)
        if slice_idx is not None:
            inputs['slice_idx'] = slice_idx

        self.report('Get or guess initial window.')
        wannier_bands = self.ctx.fp_run.outputs.wannier_bands
        initial_window = self.inputs.get('initial_window', None)
        if initial_window is None:
            initial_window = get_initial_window_inline(
                wannier_bands=wannier_bands,
                slice_reference_bands=self.inputs.get(
                    'slice_reference_bands',
                    List(list=range(wannier_bands.get_bands().shape[1]))
                )
            )[1]

        self.report("Starting WindowSearch workflow.")
        return ToContext(
            window_search=self.submit(
                WindowSearch,
                reference_bands=reference_bands,
                wannier_bands=wannier_bands,
                wannier_parameters=self.ctx.fp_run.outputs.wannier_parameters,
                wannier_input_folder=self.ctx.fp_run.outputs.
                wannier_input_folder,
                wannier_settings=wannier_settings,
                wannier_projections=wannier_projections,
                initial_window=initial_window,
                **inputs
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the outputs of the window_search sub-workflow.
        """
        self.report("Adding outputs from WindowSearch workflow.")
        window_search = self.ctx.window_search
        for label, node in window_search.get_outputs(
            also_labels=True, link_type=LinkType.RETURN
        ):
            self.out(label, node)
