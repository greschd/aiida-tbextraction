# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines inline calculations to automatically get an initial window guess.
"""

import numpy as np

from aiida import orm
from aiida.engine import calcfunction

from .._calcfunctions import merge_nested_dict


@calcfunction
def get_initial_window_inline(wannier_bands, slice_reference_bands):
    """
    InlineCalculation which returns the automatic guess for the window based on the Wannier bands.

    Arguments
    ---------
    wannier_bands : aiida.orm.data.array.bands.BandsData
        Bands calculated for the Wannier run.
    slice_reference_bands : aiida.orm.data.list.List
        Indices of the reference bands which should be considered.
    """
    return orm.List(
        list=guess_window(
            wannier_bands=wannier_bands,
            slice_reference_bands=slice_reference_bands
        )
    )


@calcfunction
def add_initial_window_inline(
    wannier_parameters, wannier_bands, slice_reference_bands
):
    """
    InlineCalculation which adds the automatic guess for the window to an
    existing Wannier input parameter set.

    Arguments
    ---------
    wannier_parameters: aiida.orm.data.parameter.ParameterData
        Initial Wannier input parameters.
    wannier_bands : aiida.orm.data.array.bands.BandsData
        Bands calculated for the Wannier run.
    slice_reference_bands : aiida.orm.data.list.List
        Indices of the reference bands which should be considered.
    """
    wannier_param_dict = wannier_parameters.get_dict()
    window_keys = [
        'dis_win_min', 'dis_froz_min', 'dis_froz_max', 'dis_win_max'
    ]
    # Check if disentanglement is needed.
    if (('num_bands' not in wannier_param_dict) or (
        int(wannier_param_dict['num_bands']
            ) == int(wannier_param_dict['num_wann'])
    )):
        return {'result': orm.Dict(dict=wannier_param_dict)}
    else:
        window_dict = {
            key: value
            for key, value in zip(
                window_keys,
                guess_window(
                    wannier_bands=wannier_bands,
                    slice_reference_bands=slice_reference_bands
                )
            )
        }
        return merge_nested_dict(
            dict_primary=wannier_parameters,
            dict_secondary=orm.Dict(dict=window_dict)
        )


def guess_window(wannier_bands, slice_reference_bands):
    """
    Creates the maximal (up to delta = 0.01) inner and minimal outer energy windows, based the given reference bands.
    """
    delta = 0.01
    bands_sliced = wannier_bands.get_bands()[:, list(slice_reference_bands)]
    lowest_band = bands_sliced[:, 0]
    highest_band = bands_sliced[:, -1]
    outer_lower = np.min(lowest_band) - delta
    outer_upper = np.max(highest_band) + delta
    inner_lower = np.max(lowest_band) + delta
    inner_upper = np.min(highest_band) - delta
    return [outer_lower, inner_lower, inner_upper, outer_upper]
