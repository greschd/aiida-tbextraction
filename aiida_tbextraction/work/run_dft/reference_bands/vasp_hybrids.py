import numpy as np
from aiida.orm import Code, DataFactory, CalculationFactory
from aiida.work.run import submit
from aiida.work.workchain import ToContext
from aiida.orm.calculation.inline import make_inline

from .base import ReferenceBandsBase
from ..._utils import check_workchain_step


class VaspHybridsBands(ReferenceBandsBase):
    """
    The WorkChain to calculate reference bands with VASP, using hybrids.
    """

    @classmethod
    def define(cls, spec):
        super(VaspHybridsBands, cls).define(spec)
        # For this workflow, the kpoints_mesh input is actually required
        spec.input('kpoints_mesh', valid_type=DataFactory('array.kpoints'))

        ParameterData = DataFactory('parameter')
        spec.input('code', valid_type=Code)
        spec.input('parameters', valid_type=ParameterData)
        spec.input('calculation_kwargs', valid_type=ParameterData)

        spec.outline(cls.run_calc, cls.get_bands)

    @check_workchain_step
    def run_calc(self):
        self.report("Merging kpoints and kpoints_mesh.")
        mesh_kpoints = self.inputs.kpoints_mesh
        band_kpoints = self.inputs.kpoints
        kpoints = merge_kpoints_inline(
            mesh_kpoints=mesh_kpoints, band_kpoints=band_kpoints
        )[1]['kpoints']

        self.report("Submitting VASP calculation.")
        return ToContext(
            vasp_calc=submit(
                CalculationFactory('vasp.vasp').process(),
                structure=self.inputs.structure,
                paw=self.inputs.potentials,
                kpoints=kpoints,
                parameters=self.inputs.parameters,
                code=self.inputs.code,
                **self.inputs.calculation_kwargs.get_dict()
            )
        )

    @check_workchain_step
    def get_bands(self):
        bands = self.ctx.vasp_calc.out.bands
        cropped_bands = crop_bands_inline(
            bands=bands, kpoints=self.inputs.kpoints
        )[1]['bands']
        self.out('bands', cropped_bands)


@make_inline
def merge_kpoints_inline(mesh_kpoints, band_kpoints):
    """
    Merges the kpoints of mesh_kpoints and band_kpoints (in that order), giving weight 1 to the mesh_kpoints, and weight 0 to the band_kpoints.
    """
    band_kpoints_array = band_kpoints.get_kpoints()
    mesh_kpoints_array = mesh_kpoints.get_kpoints_mesh(print_list=True)
    weights = [1.] * len(mesh_kpoints_array) + [0.] * len(band_kpoints_array)
    kpoints = DataFactory('array.kpoints')()
    kpoints.set_kpoints(
        np.vstack([mesh_kpoints_array, band_kpoints_array]), weights=weights
    )
    return {'kpoints': kpoints}


@make_inline
def crop_bands_inline(bands, kpoints):
    """
    Crop a BandsData to the given kpoints by removing from the front.
    """
    # check consistency of kpoints
    kpoints_array = kpoints.get_kpoints()
    band_slice = slice(-len(kpoints_array), None)
    cropped_bands_kpoints = bands.get_kpoints()[band_slice]
    assert np.allclose(cropped_bands_kpoints, kpoints_array)

    cropped_bands = DataFactory('array.bands')()
    cropped_bands.set_kpointsdata(kpoints)
    bands_array = bands.get_bands()
    assert len(bands_array) == 1
    cropped_bands_array = bands_array[0, band_slice]
    cropped_bands.set_bands(cropped_bands_array)
    return {'bands': cropped_bands}
