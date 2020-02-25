# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow for calculating a tight-binding model for a given Wannier90 input and symmetries.
"""

from collections import ChainMap

from aiida import orm
from aiida.plugins import CalculationFactory
from aiida.engine import WorkChain, if_, ToContext

from aiida_tools import check_workchain_step
from aiida_wannier90.calculations import Wannier90Calculation

__all__ = ('TightBindingCalculation', )


class TightBindingCalculation(WorkChain):
    """
    This workchain creates a tight-binding model from the Wannier90 input and a symmetry file.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input(
            'structure',
            valid_type=orm.StructureData,
            help=
            'Structure of the material for which the tight-binding model should be calculated.'
        )
        spec.expose_inputs(
            Wannier90Calculation, namespace='wannier', exclude=('structure', )
        )

        spec.input(
            'code_tbmodels',
            valid_type=orm.Code,
            help='Code that runs the TBmodels CLI.'
        )
        spec.input(
            'slice_idx',
            valid_type=orm.List,
            required=False,
            help=
            'Indices of the orbitals which are sliced (selected) from the tight-binding model. This can be used to either reduce the number of orbitals, or re-order the orbitals.'
        )
        spec.input(
            'symmetries',
            valid_type=orm.SinglefileData,
            required=False,
            help=
            'File containing the symmetries which will be applied to the tight-binding model. The file must be in ``symmetry-representation`` HDF5 format.'
        )
        spec.output(
            'tb_model',
            valid_type=orm.SinglefileData,
            help='The calculated tight-binding model, in TBmodels HDF5 format.'
        )

        spec.outline(
            cls.run_wannier, cls.parse,
            if_(cls.has_slice)(cls.slice),
            if_(cls.has_symmetries)(cls.symmetrize), cls.finalize
        )

    def has_slice(self):
        return 'slice_idx' in self.inputs

    def has_symmetries(self):
        return 'symmetries' in self.inputs

    @check_workchain_step
    def run_wannier(self):
        """
        Run the Wannier90 calculation.
        """
        wannier_inputs = self.exposed_inputs(
            Wannier90Calculation, namespace='wannier'
        )
        wannier_parameters = wannier_inputs['parameters'].get_dict()
        wannier_parameters.setdefault('write_hr', True)
        wannier_parameters.setdefault('write_xyz', True)
        wannier_parameters.setdefault('use_ws_distance', True)
        self.report("Running Wannier90 calculation.")

        wannier_inputs['parameters'] = orm.Dict(dict=wannier_parameters)
        wannier_inputs['settings'] = orm.Dict(
            dict=ChainMap(
                wannier_inputs.get('settings', orm.Dict()).get_dict(),
                {"additional_retrieve_list": ['*.win']}
            )
        )

        return ToContext(
            wannier_calc=self.submit(
                Wannier90Calculation,
                structure=self.inputs.structure,
                **wannier_inputs
            )
        )

    def setup_tbmodels(self, calc_string):
        """
        Helper function to create the builder for TBmodels calculations.
        """
        builder = CalculationFactory(calc_string).get_builder()
        builder.code = self.inputs.code_tbmodels
        builder.metadata.options = dict(
            resources={'num_machines': 1}, withmpi=False
        )
        return builder

    @property
    def tb_model(self):
        return self.ctx.tbmodels_calc.outputs.tb_model

    @check_workchain_step
    def parse(self):
        """
        Runs the calculation to parse the Wannier90 output.
        """
        builder = self.setup_tbmodels('tbmodels.parse')
        builder.wannier_folder = self.ctx.wannier_calc.outputs.retrieved
        builder.pos_kind = orm.Str('nearest_atom')
        self.report("Parsing Wannier90 output to tbmodels format.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def slice(self):
        """
        Runs the calculation that slices (re-orders) the orbitals.
        """
        builder = self.setup_tbmodels('tbmodels.slice')
        builder.tb_model = self.tb_model
        builder.slice_idx = self.inputs.slice_idx
        self.report("Slicing tight-binding model.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def symmetrize(self):
        """
        Runs the symmetrization calculation.
        """
        builder = self.setup_tbmodels('tbmodels.symmetrize')
        builder.tb_model = self.tb_model
        builder.symmetries = self.inputs.symmetries
        self.report("Symmetrizing tight-binding model.")
        return ToContext(tbmodels_calc=self.submit(builder))

    @check_workchain_step
    def finalize(self):
        """
        Adds the final tight-binding model to the output.
        """
        self.out("tb_model", self.tb_model)
        self.report('Adding tight-binding model to results.')
