# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines helper inline calculations.
"""

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from fsc.export import export

from aiida.orm.data.parameter import ParameterData
from aiida.orm.calculation.inline import make_inline


@export
@make_inline
def merge_parameterdata_inline(param_primary, param_secondary):
    """
    Merges two ParameterData, giving preference to ``param_primary``.
    """
    return ParameterData(
        dict=ChainMap(param_primary.get_dict(), param_secondary.get_dict())
    )


@export
@make_inline
def slice_bands_inline(bands, slice_idx):
    """
    Slices the given BandsData such that only the bands given in ``slice_idx``
    remain, in the given order.  The k-points remain unchanged.
    """
    result = bands.clone()
    result.set_bands(result.get_bands()[:, slice_idx.get_attr('list')])
    return result
