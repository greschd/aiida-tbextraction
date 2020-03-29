# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow for calculating a tight-binding model for a given Wannier90 input and symmetries.
"""

from collections import ChainMap

from aiida import orm
from aiida.engine import WorkChain, if_, ToContext

from aiida_tools import check_workchain_step
from aiida_tbmodels.workflows.parse import ParseWorkChain
from aiida_tbmodels.calculations.slice import SliceCalculation
from aiida_tbmodels.calculations.symmetrize import SymmetrizeCalculation
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
        spec.expose_inputs(
            ParseWorkChain,
            namespace='parse',
            exclude=('calc.code', 'calc.wannier_folder'),
            namespace_options={
                'help': 'Parameters passed to the tbmodels parse workflow.'
            }
        )
        # Change the default for 'pos_kind' to 'nearest_atom'.
        spec.inputs['parse']['calc'][
            'pos_kind'].default = lambda: orm.Str('nearest_atom')

        spec.expose_inputs(
            SliceCalculation,
            namespace='slice',
            exclude=('code', 'tb_model', 'slice_idx'),
            namespace_options={
                'help': 'Parameters passed to the tbmodels slice calculation.'
            }
        )
        spec.expose_inputs(SliceCalculation, include=('slice_idx', ))
        spec.inputs['slice_idx'].required = False

        spec.expose_inputs(
            SymmetrizeCalculation,
            namespace='symmetrize',
            exclude=('code', 'symmetries', 'tb_model'),
            namespace_options={
                'help':
                'Parameters passed to the tbmodels symmetrize calculation.'
            }
        )
        spec.expose_inputs(SymmetrizeCalculation, include=('symmetries', ))
        spec.inputs['symmetries'].required = False

        spec.input(
            'code_tbmodels',
            valid_type=orm.Code,
            help='Code that runs the TBmodels CLI.'
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

    @property
    def tb_model(self):
        return self.ctx.tbmodels_calc.outputs.tb_model

    @check_workchain_step
    def parse(self):
        """
        Runs the calculation to parse the Wannier90 output.
        """
        inputs = self.exposed_inputs(ParseWorkChain, namespace='parse')

        inputs['calc'].setdefault('code', self.inputs.code_tbmodels)
        inputs['calc']['wannier_folder'
                       ] = self.ctx.wannier_calc.outputs.retrieved

        self.report("Parsing Wannier90 output to tbmodels format.")
        return ToContext(tbmodels_calc=self.submit(ParseWorkChain, **inputs))

    @check_workchain_step
    def slice(self):
        """
        Runs the calculation that slices (re-orders) the orbitals.
        """
        inputs = self.exposed_inputs(SliceCalculation, namespace='slice')
        inputs['tb_model'] = self.tb_model
        inputs.setdefault('code', self.inputs.code_tbmodels)
        self.report("Slicing tight-binding model.")
        return ToContext(tbmodels_calc=self.submit(SliceCalculation, **inputs))

    @check_workchain_step
    def symmetrize(self):
        """
        Runs the symmetrization calculation.
        """

        inputs = self.exposed_inputs(
            SymmetrizeCalculation, namespace='symmetrize'
        )
        inputs.setdefault('code', self.inputs.code_tbmodels)
        inputs['tb_model'] = self.tb_model
        self.report("Symmetrizing tight-binding model.")
        return ToContext(
            tbmodels_calc=self.submit(SymmetrizeCalculation, **inputs)
        )

    @check_workchain_step
    def finalize(self):
        """
        Adds the final tight-binding model to the output.
        """
        self.out("tb_model", self.tb_model)
        self.report('Adding tight-binding model to results.')
