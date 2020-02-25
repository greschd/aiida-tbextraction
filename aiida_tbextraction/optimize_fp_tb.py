# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the workflow that runs first-principles calculations and creates an optimized tight-binding model.
"""

import contextlib
from collections import ChainMap

from aiida import orm
from aiida.engine import WorkChain, ToContext
from aiida.common.exceptions import NotExistent

from aiida_tools import check_workchain_step, get_outputs_dict
from aiida_tools.process_inputs import PROCESS_INPUT_KWARGS, load_object

from .energy_windows.window_search import WindowSearch
from .fp_run import FirstPrinciplesRunBase
from ._calcfunctions import merge_nested_dict, slice_bands_inline
from .energy_windows.auto_guess import get_initial_window_inline

__all__ = ('OptimizeFirstPrinciplesTightBinding', )


class OptimizeFirstPrinciplesTightBinding(WorkChain):
    """
    Creates a tight-binding model by first running first-principles calculations to get a reference bandstructure and Wannier90 input, and then optimizing the energy window to get an optimized symmetric tight-binding model.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

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
                'reference_bands',
                'wannier_bands',
                'wannier.parameters',
                'wannier.local_input_folder',
                'wannier.remote_input_folder',
                'slice_idx',
            )
        )
        # Workaround for plumpy issue #135 (https://github.com/aiidateam/plumpy/issues/135)
        spec.inputs['model_evaluation'].dynamic = True

        # initial window is not required because it can be guessed.
        spec.input(
            'initial_window',
            valid_type=orm.List,
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
            valid_type=orm.List,
            required=False,
            help=
            'Indices for the reference bands which should be included in the model evaluation.'
        )
        spec.input(
            'slice_tb_model',
            valid_type=orm.List,
            required=False,
            help='Indices for slicing (re-ordering) the tight-binding model.'
        )

        spec.expose_outputs(WindowSearch)
        spec.outputs.dynamic = True

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

        fp_run_outputs = self.ctx.fp_run.outputs
        wannier_namespace_inputs = inputs.pop('wannier', {})

        with contextlib.suppress(NotExistent, KeyError):
            wannier_settings_explicit = wannier_namespace_inputs['settings']
            wannier_settings_from_wf = fp_run_outputs.wannier_settings
            wannier_namespace_inputs['settings'] = merge_nested_dict(
                dict_primary=wannier_settings_explicit,
                dict_secondary=wannier_settings_from_wf
            )

        with contextlib.suppress(NotExistent):
            wannier_namespace_inputs['projections'
                                     ] = fp_run_outputs.wannier_projections

        wannier_namespace_inputs['parameters'
                                 ] = fp_run_outputs.wannier_parameters
        wannier_namespace_inputs['local_input_folder'
                                 ] = fp_run_outputs.wannier_input_folder

        # slice reference bands if necessary
        reference_bands = fp_run_outputs.bands
        slice_reference_bands = self.inputs.get('slice_reference_bands', None)
        if slice_reference_bands is not None:
            reference_bands = slice_bands_inline(
                bands=reference_bands, slice_idx=slice_reference_bands
            )

        # get slice_idx for window_search
        slice_idx = self.inputs.get('slice_tb_model', None)
        if slice_idx is not None:
            inputs['slice_idx'] = slice_idx

        self.report('Get or guess initial window.')
        wannier_bands = fp_run_outputs.wannier_bands
        initial_window = self.inputs.get('initial_window', None)
        if initial_window is None:
            initial_window = get_initial_window_inline(
                wannier_bands=wannier_bands,
                slice_reference_bands=self.inputs.get(
                    'slice_reference_bands',
                    orm.List(
                        list=list(range(wannier_bands.get_bands().shape[1]))
                    )
                )
            )

        self.report("Starting WindowSearch workflow.")
        return ToContext(
            window_search=self.submit(
                WindowSearch,
                reference_bands=reference_bands,
                wannier=wannier_namespace_inputs,
                wannier_bands=wannier_bands,
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
        self.out_many(get_outputs_dict(self.ctx.window_search))
