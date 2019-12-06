# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines helper InlineCalculations for the first-principles workflows.
"""

from aiida.engine import calcfunction


@calcfunction
def flatten_bands_inline(bands):
    """
    Flatten the bands such that they have dimension 2.
    """
    flattened_bands = bands.clone()
    bands_array = bands.get_bands()
    flattened_bands.set_bands(bands_array.reshape(bands_array.shape[-2:]))

    return flattened_bands


# @calcfunction
# def reduce_num_wann_inline(wannier_parameters):
#     """
#     Reduces the ``num_wann`` in a Wannier90 input by the number of bands
#     in its ``exclude_bands`` parameter.
#     """
#     wannier_param_dict = wannier_parameters.get_dict()
#     if 'exclude_bands' in wannier_param_dict and 'num_bands' in wannier_param_dict:
#         exclude_bands_val = wannier_param_dict['exclude_bands']
#         if not isinstance(exclude_bands_val, str):
#             raise ValueError(
#                 "Invalid value for 'exclude_bands': '{}'".
#                 format(exclude_bands_val)
#             )
#         num_excluded = 0
#         for part in exclude_bands_val.split(','):
#             if '-' in part:
#                 lower, upper = [int(x) for x in part.split('-')]
#                 diff = (upper - lower) + 1
#                 assert diff > 0
#                 num_excluded += diff
#             else:
#                 num_excluded += 1
#         wannier_param_dict['num_bands'] = int(
#             wannier_param_dict['num_bands']
#         ) - num_excluded
#         return orm.Dict(dict=wannier_param_dict)
#     else:
#         return wannier_parameters
