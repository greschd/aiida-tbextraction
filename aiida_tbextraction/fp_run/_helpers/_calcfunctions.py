# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines helper calcfunctions for the first-principles workflows.
"""

import itertools

import numpy as np

from aiida import orm
from aiida.engine import calcfunction


@calcfunction
def flatten_bands(bands):
    """
    Flatten the bands such that they have dimension 2.
    """
    flattened_bands = bands.clone()
    bands_array = bands.get_bands()
    flattened_bands.set_bands(bands_array.reshape(bands_array.shape[-2:]))

    return flattened_bands


@calcfunction
def make_explicit_kpoints(kpoints_mesh):
    """
    Creates an explicit KpointsData from a KpointsData specified as
    a mesh.
    """
    mesh, offset = kpoints_mesh.get_kpoints_mesh()

    kpts_explicit_array = np.array(
        list(
            itertools.product(
                *[
                    np.linspace(0, 1, mesh_size, endpoint=False)
                    for mesh_size in mesh
                ]
            )
        )
    )
    kpts_explicit_array += offset
    kpts_explicit = orm.KpointsData()
    kpts_explicit.set_kpoints(kpts_explicit_array)
    return kpts_explicit


@calcfunction
def reduce_num_bands(wannier_parameters):
    """
    Reduces the ``num_bands`` in a Wannier90 input by the number of bands
    in its ``exclude_bands`` parameter.
    """
    wannier_param_dict = wannier_parameters.get_dict()
    if 'exclude_bands' in wannier_param_dict and 'num_bands' in wannier_param_dict:
        exclude_bands_val = wannier_param_dict.pop('exclude_bands')
        if not isinstance(exclude_bands_val, str):
            raise ValueError(
                "Invalid value for 'exclude_bands': '{}'".
                format(exclude_bands_val)
            )
        num_excluded = 0
        for part in exclude_bands_val.split(','):
            if '-' in part:
                lower, upper = [int(x) for x in part.split('-')]
                diff = (upper - lower) + 1
                assert diff > 0
                num_excluded += diff
            else:
                num_excluded += 1
        wannier_param_dict['num_bands'] = int(
            wannier_param_dict['num_bands']
        ) - num_excluded
        return orm.Dict(dict=wannier_param_dict)
    else:
        return wannier_parameters


@calcfunction
def crop_bands(bands, kpoints):
    """
    Crop a BandsData to the given kpoints by removing from the front.
    """
    # check consistency of kpoints
    kpoints_array = kpoints.get_kpoints()
    band_slice = slice(-len(kpoints_array), None)
    cropped_bands_kpoints = bands.get_kpoints()[band_slice]
    assert np.allclose(cropped_bands_kpoints, kpoints_array)

    cropped_bands = orm.BandsData()
    cropped_bands.set_kpointsdata(kpoints)
    cropped_bands_array = bands.get_bands()[band_slice]
    cropped_bands.set_bands(cropped_bands_array)
    return cropped_bands


@calcfunction
def merge_kpoints(mesh_kpoints, band_kpoints):
    """
    Merges the kpoints of mesh_kpoints and band_kpoints (in that order), giving weight 1 to the mesh_kpoints, and weight 0 to the band_kpoints.
    """
    band_kpoints_array = band_kpoints.get_kpoints()
    mesh_kpoints_array = mesh_kpoints.get_kpoints_mesh(print_list=True)
    weights = [1.] * len(mesh_kpoints_array) + [0.] * len(band_kpoints_array)
    kpoints = orm.KpointsData()
    kpoints.set_kpoints(
        np.vstack([mesh_kpoints_array, band_kpoints_array]), weights=weights
    )
    return kpoints
