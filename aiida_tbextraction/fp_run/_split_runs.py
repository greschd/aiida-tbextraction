"""
Defines a workflow for independently running the bands and Wannier input calculations.
"""

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.work.workchain import ToContext

from aiida_tools import check_workchain_step
from aiida_tools.workchain_inputs import WORKCHAIN_INPUT_KWARGS, load_object

from ._base import FirstPrinciplesRunBase
from .reference_bands import ReferenceBandsBase
from .wannier_input import WannierInputBase


@export
class SplitFirstPrinciplesRun(FirstPrinciplesRunBase):
    """
    Independently runs the DFT calculations for creating the reference bands and Wannier90 input.
    """

    @classmethod
    def define(cls, spec):
        super(SplitFirstPrinciplesRun, cls).define(spec)

        spec.input('reference_bands_workflow', **WORKCHAIN_INPUT_KWARGS)
        spec.input('wannier_input_workflow', **WORKCHAIN_INPUT_KWARGS)

        # Add dynamic namespaces
        spec.input_namespace('reference_bands', dynamic=True)
        spec.input_namespace('wannier_input', dynamic=True)

        spec.outline(cls.fp_run, cls.finalize)

    @check_workchain_step
    def fp_run(self):
        """
        Run the first-principles calculation workflows.
        """
        self.report('Submitting reference_bands workflow.')
        reference_bands = self.submit(
            load_object(self.inputs.reference_bands_workflow),
            **ChainMap(
                self.inputs['reference_bands'],
                self.exposed_inputs(
                    ReferenceBandsBase, namespace='reference_bands'
                )
            )
        )
        self.report('Submitting wannier_input workflow.')
        wannier_input = self.submit(
            load_object(self.inputs.wannier_input_workflow),
            **ChainMap(
                self.inputs['wannier_input'],
                self.exposed_inputs(
                    WannierInputBase, namespace='wannier_input'
                )
            )
        )
        return ToContext(
            reference_bands=reference_bands, wannier_input=wannier_input
        )

    @check_workchain_step
    def finalize(self):
        """
        Add the outputs of the first-principles workflows.
        """
        self.report('Add reference bands outputs.')
        self.out_many(
            self.exposed_outputs(self.ctx.reference_bands, ReferenceBandsBase)
        )
        self.report('Add Wannier input outputs.')
        self.out_many(
            self.exposed_outputs(self.ctx.wannier_input, WannierInputBase)
        )
