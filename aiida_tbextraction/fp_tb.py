# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the workflow that runs first-principles calculations and creates a
tight-binding model, without running the window optimization.
"""

from collections import ChainMap

from aiida import orm
from aiida.engine import WorkChain, ToContext
from aiida.common.exceptions import NotExistent

from aiida_tools import check_workchain_step, get_outputs_dict
from aiida_tools.process_inputs import PROCESS_INPUT_KWARGS, load_object

from .model_evaluation import ModelEvaluationBase
from .calculate_tb import TightBindingCalculation
from .fp_run import FirstPrinciplesRunBase
from .energy_windows.auto_guess import add_initial_window_inline
from ._calcfunctions import merge_nested_dict, slice_bands_inline

__all__ = ('FirstPrinciplesTightBinding', )


class FirstPrinciplesTightBinding(WorkChain):
    """
    Creates a tight-binding model by first running first-principles calculations to get a reference bandstructure and Wannier90 input, and then calculating the tight-binding model.
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
        spec.input(
            'fp_run_workflow',
            help='Workflow which executes the first-principles calculations',
            **PROCESS_INPUT_KWARGS
        )

        # top-level scope
        spec.expose_inputs(
            TightBindingCalculation,
            exclude=(
                'wannier.parameters',
                'wannier.bands',
                'wannier.kpoints',
                'wannier.local_input_folder',
                'wannier.remote_input_folder',
                'slice_idx',
            )
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
        spec.input(
            'guess_windows',
            valid_type=orm.Bool,
            default=lambda: orm.Bool(False),
            help='Add disentanglement windows guessed from the wannier bands.'
        )

        spec.expose_inputs(
            ModelEvaluationBase, exclude=['tb_model', 'reference_bands']
        )
        spec.input_namespace(
            'model_evaluation',
            dynamic=True,
            help=
            'Inputs that will be passed to the ``model_evaluation_workflow``.'
        )
        spec.input(
            'model_evaluation_workflow',
            help=
            'AiiDA workflow that will be used to evaluate the tight-binding model.',
            **PROCESS_INPUT_KWARGS
        )

        spec.expose_outputs(TightBindingCalculation)
        spec.expose_outputs(ModelEvaluationBase)
        # Allow returning outputs from ModelEvaluationBase sub-classes.
        spec.outputs.dynamic = True

        spec.outline(cls.fp_run, cls.run_tb, cls.run_evaluate, cls.finalize)

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
    def run_tb(self):
        """
        Runs the workflow which creates the tight-binding model.
        """
        # check for wannier_settings from wannier_input workflow
        inputs = self.exposed_inputs(TightBindingCalculation)
        self.report(
            "Merging 'wannier_settings' from input and wannier_input workflow."
        )
        wannier_namespace_inputs = inputs.pop('wannier', {})

        # merge settings
        wannier_settings_explicit = wannier_namespace_inputs.pop(
            'settings', orm.Dict()
        )
        try:
            wannier_settings_from_wf = self.ctx.fp_run.outputs.wannier_settings
            wannier_namespace_inputs['settings'] = merge_nested_dict(
                dict_primary=wannier_settings_explicit,
                dict_secondary=wannier_settings_from_wf
            )
        except NotExistent:
            wannier_namespace_inputs['settings'] = wannier_settings_explicit

        # prefer wannier_projections from wannier_input workflow if it exists
        wannier_projections_explicit = wannier_namespace_inputs.pop(
            'projections', None
        )
        try:
            wannier_namespace_inputs[
                'projections'] = self.ctx.fp_run.outputs.wannier_projections
        except NotExistent:
            wannier_namespace_inputs['projections'
                                     ] = wannier_projections_explicit

        # get slice_idx for tight-binding calculation
        slice_idx = self.inputs.get('slice_tb_model', None)
        if slice_idx is not None:
            inputs['slice_idx'] = slice_idx

        # get automatic guess for windows if needed
        wannier_bands = self.ctx.fp_run.outputs.wannier_bands
        wannier_parameters = self.ctx.fp_run.outputs.wannier_parameters
        if self.inputs.guess_windows:
            wannier_parameters = add_initial_window_inline(
                wannier_parameters=wannier_parameters,
                wannier_bands=wannier_bands,
                slice_reference_bands=self.inputs.get(
                    'slice_reference_bands',
                    orm.List(list=range(wannier_bands.get_bands().shape[1]))
                )
            )[1]

        self.report("Starting TightBindingCalculation workflow.")
        return ToContext(
            tbextraction_calc=self.submit(
                TightBindingCalculation,
                wannier=dict(
                    kpoints=wannier_bands,
                    parameters=wannier_parameters,
                    local_input_folder=self.ctx.fp_run.outputs.
                    wannier_input_folder,
                    **wannier_namespace_inputs
                ),
                **inputs
            )
        )

    @check_workchain_step
    def run_evaluate(self):
        """
        Runs the model evaluation workflow.
        """
        tb_model = self.ctx.tbextraction_calc.outputs.tb_model
        self.report("Adding tight-binding model to output.")
        self.out('tb_model', tb_model)

        # slice reference bands if necessary
        reference_bands = self.ctx.fp_run.outputs.bands
        slice_reference_bands = self.inputs.get('slice_reference_bands', None)
        if slice_reference_bands is not None:
            reference_bands = slice_bands_inline(
                bands=reference_bands, slice_idx=slice_reference_bands
            )
        self.report('Starting model evaluation workflow.')
        return ToContext(
            model_evaluation_wf=self.submit(
                load_object(self.inputs.model_evaluation_workflow),
                tb_model=tb_model,
                reference_bands=reference_bands,
                **ChainMap(
                    self.inputs.model_evaluation,
                    self.exposed_inputs(ModelEvaluationBase),
                )
            )
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the outputs from the evaluation workflow.
        """
        self.report("Adding outputs from model evaluation workflow.")
        self.out_many(get_outputs_dict(self.ctx.model_evaluation_wf))
