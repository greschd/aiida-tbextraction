# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow that calculates the Wannier90 input files using Quantum ESPRESSO pw.x.
"""

from aiida import orm
from aiida.engine import ToContext
from aiida.common.exceptions import InputValidationError

from aiida_tools import check_workchain_step
from aiida_wannier90.calculations import Wannier90Calculation
from aiida_quantumespresso.calculations.pw import PwCalculation
from aiida_quantumespresso.calculations.pw2wannier90 import Pw2wannier90Calculation

from . import WannierInputBase

from .._helpers._calcfunctions import make_explicit_kpoints
from ..._calcfunctions import merge_nested_dict

__all__ = ("QuantumEspressoWannierInput", )


class QuantumEspressoWannierInput(WannierInputBase):
    """
    Calculates the Wannier90 input files using Quantum ESPRESSO / pw2wannier90.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.expose_inputs(Wannier90Calculation, include=['structure'])
        spec.expose_inputs(
            Wannier90Calculation,
            exclude=['structure', 'kpoints', 'projections', 'parameters'],
            namespace='wannier'
        )

        spec.expose_inputs(PwCalculation, include=['structure'])
        spec.expose_inputs(
            PwCalculation, namespace='nscf', exclude=['structure', 'kpoints']
        )

        spec.expose_inputs(
            Pw2wannier90Calculation,
            namespace='pw2wannier',
            exclude=['parent_folder', 'nnkp_file']
        )

        # Exposing inputs from a calculation incorrectly sets the
        # calcjob validator, see aiida-core issue #3449
        spec.inputs.validator = None

        spec.outline(
            cls.run_nscf, cls.run_wannier90_preproc, cls.run_pw2wannier90,
            cls.get_result
        )

    @check_workchain_step
    def run_nscf(self):
        """
        Run the NSCF and wannier90 -pp calculation.
        """
        self.report("Submitting pw.x NSCF calculation.")
        nscf_inputs = self.exposed_inputs(PwCalculation, namespace='nscf')
        nscf_inputs['parameters'] = merge_nested_dict(
            orm.Dict(
                dict={
                    'CONTROL': {
                        'calculation': 'nscf'
                    },
                    'SYSTEM': {
                        'nosym': True
                    }
                }
            ), nscf_inputs.get('parameters', orm.Dict())
        )
        return ToContext(
            nscf=self.submit(
                PwCalculation,
                kpoints=make_explicit_kpoints(self.inputs.kpoints_mesh),
                **nscf_inputs
            )
        )

    @check_workchain_step
    def run_wannier90_preproc(self):
        """
        Run Wannier90 with the -pp option to create the nnkp file.
        """
        self.report("Submitting wannier90 -pp calculation.")

        wannier_parameters_input = self.inputs.get(
            'wannier_parameters', orm.Dict()
        )
        nscf_bands = self.ctx.nscf.outputs.output_band
        num_bands = nscf_bands.attributes['array|bands'][-1]
        if 'num_bands' in wannier_parameters_input.keys():
            if num_bands != wannier_parameters_input['num_bands']:
                raise InputValidationError((
                    "The 'num_bands' specified in 'wannier_parameters' ({}) "
                    "does not match the number of bands ({}) of the NSCF calculation."
                ).format(wannier_parameters_input['num_bands'], num_bands))
        wannier_parameters = merge_nested_dict(
            orm.Dict(
                dict={
                    'num_bands': num_bands,
                    'mp_grid': self.inputs.kpoints_mesh.get_kpoints_mesh()[0]
                },
            ), wannier_parameters_input
        )

        self.out('wannier_parameters', wannier_parameters)
        if 'num_wann' not in wannier_parameters.keys():
            raise InputValidationError(
                "The target number of Wannier functions 'num_wann' is not specified."
            )

        projections_input = {}
        if 'wannier_projections' in self.inputs:
            projections_input['projections'] = self.inputs.wannier_projections
        return ToContext(
            wannier90_preproc=self.submit(
                Wannier90Calculation,
                kpoints=nscf_bands,
                settings=orm.Dict(dict={'postproc_setup': True}),
                parameters=wannier_parameters,
                **projections_input,
                **
                self.exposed_inputs(Wannier90Calculation, namespace='wannier')
            )
        )

    @check_workchain_step
    def run_pw2wannier90(self):
        """
        Run the pw2wannier90 calculation.
        """
        self.report("Submitting pw2wannier90 calculation.")
        return ToContext(
            pw2wannier90=self.submit(
                Pw2wannier90Calculation,
                parent_folder=self.ctx.nscf.outputs.remote_folder,
                nnkp_file=self.ctx.wannier90_preproc.outputs.nnkp_file,
                settings=orm.Dict(
                    dict={
                        'ADDITIONAL_RETRIEVE_LIST':
                        ['aiida.mmn', 'aiida.eig', 'aiida.amn']
                    }
                ),
                **self.exposed_inputs(
                    Pw2wannier90Calculation, namespace='pw2wannier'
                ),
            )
        )

    @check_workchain_step
    def get_result(self):
        """
        Get the pw2wannier90 result and create the necessary outputs.
        """
        pw2wann_retrieved_folder = self.ctx.pw2wannier90.outputs.retrieved
        pw2wann_folder_list = pw2wann_retrieved_folder.list_object_names()
        assert all(
            filename in pw2wann_folder_list
            for filename in ['aiida.amn', 'aiida.mmn', 'aiida.eig']
        )
        self.report("Adding Wannier90 inputs to output.")
        self.out('wannier_input_folder', pw2wann_retrieved_folder)

        # The bands in aiida.eig are the same as the NSCF output up to
        # writing / parsing error.
        # NOTE: If this ends up being problematic for the 'invalid window'
        # detection, maybe add fuzzing there, since it is not possible
        # to always perfectly map aiida.eig to a floating-point value.
        # Discrepancy should be roughly ~< 1e-06
        self.out('wannier_bands', self.ctx.nscf.outputs.output_band)
        if 'wannier_projections' in self.inputs:
            self.out('wannier_projections', self.inputs.wannier_projections)
