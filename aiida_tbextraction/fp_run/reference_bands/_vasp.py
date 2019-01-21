# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines a workflow that calculates the reference bandstructure using VASP.
"""

from fsc.export import export

from aiida.orm.data.base import Bool
from aiida.orm.data.parameter import ParameterData
from aiida.orm import Code, CalculationFactory
from aiida.work.workchain import ToContext

from aiida_tools import check_workchain_step

from . import ReferenceBandsBase
from .._helpers._inline_calcs import (
    flatten_bands_inline, crop_bands_inline, merge_kpoints_inline
)


@export
class VaspReferenceBands(ReferenceBandsBase):
    """
    The WorkChain to calculate reference bands with VASP.
    """

    @classmethod
    def define(cls, spec):
        super(VaspReferenceBands, cls).define(spec)
        spec.input('code', valid_type=Code, help='Code that runs VASP.')
        spec.input(
            'parameters',
            valid_type=ParameterData,
            help='Parameters of the VASP calculation.'
        )
        spec.input_namespace(
            'calculation_kwargs',
            required=False,
            dynamic=True,
            help='Additional keyword arguments passed to the VASP calculation.'
        )
        spec.input(
            'merge_kpoints',
            valid_type=Bool,
            default=Bool(False),
            help=
            'Defines whether the k-point mesh is added to the list of k-points for the reference band calculation. This is needed for hybrid functional calculations.'
        )

        spec.outline(cls.run_calc, cls.get_bands)

    @check_workchain_step
    def run_calc(self):
        """
        Run the VASP calculation.
        """
        if self.inputs.merge_kpoints:
            self.report("Merging kpoints and kpoints_mesh.")
            mesh_kpoints = self.inputs.kpoints_mesh
            band_kpoints = self.inputs.kpoints
            kpoints = merge_kpoints_inline(
                mesh_kpoints=mesh_kpoints, band_kpoints=band_kpoints
            )[1]['kpoints']
        else:
            kpoints = self.inputs.kpoints

        self.report("Submitting VASP calculation.")
        return ToContext(
            vasp_calc=self.submit(
                CalculationFactory('vasp.vasp').process(),
                structure=self.inputs.structure,
                potential=self.inputs.potentials,
                kpoints=kpoints,
                parameters=self.inputs.parameters,
                code=self.inputs.code,
                settings=ParameterData(
                    dict=dict(parser_settings=dict(add_bands=True))
                ),
                **self.inputs.get('calculation_kwargs', {})
            )
        )

    @check_workchain_step
    def get_bands(self):
        """
        Get the bands from the VASP calculation and crop the 'mesh' k-points if necessary.
        """
        bands = self.ctx.vasp_calc.out.output_bands
        self.report("Flattening the output bands.")
        res_bands = flatten_bands_inline(bands=bands)[1]['bands']
        if self.inputs.merge_kpoints:
            self.report("Cropping mesh eigenvalues from bands.")
            res_bands = crop_bands_inline(
                bands=res_bands, kpoints=self.inputs.kpoints
            )[1]['bands']
        self.out('bands', res_bands)
