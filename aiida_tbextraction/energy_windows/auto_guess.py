# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import numpy as np

from aiida.orm.data.list import List
from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline

from .._inline_calcs import merge_parameterdata_inline


@make_inline
def get_initial_window_inline(wannier_bands, slice_reference_bands):
    return {
        'result':
        List(
            list=guess_window(
                wannier_bands=wannier_bands,
                slice_reference_bands=slice_reference_bands
            )
        )
    }


@make_inline
def add_initial_window_inline(
    wannier_parameters, wannier_bands, slice_reference_bands
):
    wannier_param_dict = wannier_parameters.get_dict()
    window_keys = [
        'dis_win_min', 'dis_froz_min', 'dis_froz_max', 'dis_win_max'
    ]
    # Check if disentanglement is needed.
    if (('num_bands' not in wannier_param_dict) or (
        int(wannier_param_dict['num_bands']
            ) == int(wannier_param_dict['num_wann'])
    )):
        return {'result': ParameterData(dict=wannier_param_dict)}
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
        return {
            'result':
            merge_parameterdata_inline(
                param_primary=wannier_parameters,
                param_secondary=ParameterData(dict=window_dict)
            )[1]
        }


def guess_window(wannier_bands, slice_reference_bands):
    DELTA = 0.01
    bands_sliced = wannier_bands.get_bands()[:, list(slice_reference_bands)]
    lowest_band = bands_sliced[:, 0]
    highest_band = bands_sliced[:, -1]
    outer_lower = np.min(lowest_band) - DELTA
    outer_upper = np.max(highest_band) + DELTA
    inner_lower = np.max(lowest_band) + DELTA
    inner_upper = np.min(highest_band) - DELTA
    return [outer_lower, inner_lower, inner_upper, outer_upper]
