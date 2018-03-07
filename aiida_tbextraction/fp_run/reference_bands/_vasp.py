import numpy as np
from fsc.export import export

from aiida.orm.data.base import Bool
from aiida.orm import Code, DataFactory, CalculationFactory
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.work.process import PortNamespace

from aiida_tools import check_workchain_step

from . import ReferenceBandsBase
from .._helpers._inline_calcs import crop_bands_inline, merge_kpoints_inline


@export  # pylint: disable=abstract-method
class VaspReferenceBands(ReferenceBandsBase):
    """
    The WorkChain to calculate reference bands with VASP.
    """

    @classmethod
    def define(cls, spec):
        super(VaspReferenceBands, cls).define(spec)
        ParameterData = DataFactory('parameter')
        spec.input('code', valid_type=Code)
        spec.input('parameters', valid_type=ParameterData)
        spec._inputs['calculation_kwargs'] = PortNamespace(
            'calculation_kwargs', required=False
        )
        spec.input('merge_kpoints', valid_type=Bool, default=Bool(False))

        spec.outline(cls.run_calc, cls.get_bands)

    @check_workchain_step
    def run_calc(self):
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
            vasp_calc=submit(
                CalculationFactory('vasp.vasp').process(),
                structure=self.inputs.structure,
                paw=self.inputs.potentials,
                kpoints=kpoints,
                parameters=self.inputs.parameters,
                code=self.inputs.code,
                **self.inputs.get('calculation_kwargs', {})
            )
        )

    @check_workchain_step
    def get_bands(self):
        bands = self.ctx.vasp_calc.out.bands
        if self.inputs.merge_kpoints:
            self.report("Cropping mesh eigenvalues from bands.")
            res_bands = crop_bands_inline(
                bands=bands, kpoints=self.inputs.kpoints
            )[1]['bands']
        else:
            res_bands = bands
        self.out('bands', res_bands)
