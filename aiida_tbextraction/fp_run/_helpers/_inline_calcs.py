"""
Defines helper InlineCalculations for the first-principles workflows.
"""

import numpy as np

from aiida.orm import DataFactory
from aiida.orm.calculation.inline import make_inline


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
def flatten_bands_inline(bands):
    """
    Flatten the bands such that they have dimension 2.
    """
    flattened_bands = bands.clone()
    bands_array = bands.get_bands()
    flattened_bands.set_bands(bands_array.reshape(bands_array.shape[-2:]))

    return {'bands': flattened_bands}


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
    cropped_bands_array = bands.get_bands()[band_slice]
    cropped_bands.set_bands(cropped_bands_array)
    return {'bands': cropped_bands}
