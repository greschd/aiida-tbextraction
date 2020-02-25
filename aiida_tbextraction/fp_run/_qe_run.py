# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow for running the first-principles calculations using Quantum ESPRESSO.
"""

from fsc.export import export

from aiida import orm
from aiida.engine import ToContext

from aiida_tools import check_workchain_step

from aiida_quantumespresso.calculations.pw import PwCalculation

from .._calcfunctions import merge_nested_dict
from .wannier_input import QuantumEspressoWannierInput
from .reference_bands import QuantumEspressoReferenceBands
from ._base import FirstPrinciplesRunBase


@export
class QuantumEspressoFirstPrinciplesRun(FirstPrinciplesRunBase):
    """Calculate Wannier90 inputs and reference bands with Quantum Espresso.

    Workflow for calculating the inputs needed for the tight-binding
    calculation and evaluation with Quantum Espresso. The workflow first
    performs an SCF step, and then passes uses the remote folder from
    that calculation as input for a bands calculation, and an NSCF +
    Wannier90 pre-processing + PW2WANNIER90 calculation for the Wannier90
    inputs.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(
            PwCalculation, namespace='scf', exclude=['structure', 'kpoints']
        )
        spec.expose_inputs(
            QuantumEspressoReferenceBands, include=['structure', 'kpoints']
        )
        spec.expose_inputs(
            QuantumEspressoReferenceBands,
            exclude=['structure', 'kpoints', 'parent_folder'],
            namespace='bands',
            namespace_options={
                'help':
                'Inputs passed to the workflow generating the reference '
                'band structure.'
            }
        )

        spec.expose_inputs(
            QuantumEspressoWannierInput, include=['structure', 'kpoints_mesh']
        )
        spec.expose_inputs(
            QuantumEspressoWannierInput,
            exclude=[
                'structure', 'kpoints_mesh', 'parent_folder',
                'wannier_parameters', 'wannier_projections'
            ],
            namespace='to_wannier',
            namespace_options={
                'help':
                'Inputs passed to the workflow generating '
                'the Wannier90 inputs.'
            }
        )

        spec.expose_outputs(QuantumEspressoReferenceBands)
        spec.expose_outputs(QuantumEspressoWannierInput)

        spec.outline(cls.run_scf, cls.run_bands_and_wannier, cls.finalize)

    @check_workchain_step
    def run_scf(self):
        """
        Run the SCF calculation step.
        """
        self.report('Launching SCF calculation.')

        inputs = self.exposed_inputs(PwCalculation, namespace='scf')
        inputs['parameters'] = merge_nested_dict(
            orm.Dict(dict={'CONTROL': {
                'calculation': 'scf'
            }}), inputs.get('parameters', orm.Dict())
        )
        return ToContext(
            scf=self.submit(
                PwCalculation,
                structure=self.inputs.structure,
                kpoints=self.inputs.kpoints_mesh,
                **inputs
            )
        )

    @check_workchain_step
    def run_bands_and_wannier(self):
        """
        Run the reference bands and wannier input workflows.
        """
        self.report('Launching bands workchain.')
        bands_inputs = self.exposed_inputs(
            QuantumEspressoReferenceBands, namespace='bands'
        )
        bands_inputs['pw']['parent_folder'
                           ] = self.ctx.scf.outputs.remote_folder
        bands_run = self.submit(QuantumEspressoReferenceBands, **bands_inputs)

        self.report('Launching to_wannier workchain.')
        wannier_inputs = self.exposed_inputs(
            QuantumEspressoWannierInput, namespace='to_wannier'
        )
        wannier_inputs['nscf']['parent_folder'
                               ] = self.ctx.scf.outputs.remote_folder

        if 'wannier_parameters' in self.inputs:
            wannier_inputs['wannier_parameters'
                           ] = self.inputs.wannier_parameters
        if 'wannier_projections' in self.inputs:
            wannier_inputs['wannier_projections'
                           ] = self.inputs.wannier_projections

        to_wannier = self.submit(QuantumEspressoWannierInput, **wannier_inputs)

        return ToContext(bands=bands_run, to_wannier=to_wannier)

    @check_workchain_step
    def finalize(self):
        """
        Add outputs of the bandstructure and wannier input calculations.
        """
        self.report('Retrieving outputs.')
        self.out_many(
            self.exposed_outputs(
                self.ctx.bands, QuantumEspressoReferenceBands
            )
        )
        self.out_many(
            self.exposed_outputs(
                self.ctx.to_wannier, QuantumEspressoWannierInput
            )
        )
