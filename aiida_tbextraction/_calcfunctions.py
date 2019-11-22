# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines helper inline calculations.
"""

from collections import ChainMap

from fsc.export import export

from aiida import orm
from aiida.engine import calcfunction


@export
@calcfunction
def merge_parameterdata_inline(param_primary, param_secondary):
    """
    Merges two ParameterData, giving preference to ``param_primary``.
    """
    return orm.Dict(
        dict=ChainMap(param_primary.get_dict(), param_secondary.get_dict())
    )


@export
@calcfunction
def slice_bands_inline(bands, slice_idx):
    """
    Slices the given BandsData such that only the bands given in ``slice_idx``
    remain, in the given order.  The k-points remain unchanged.
    """
    result = bands.clone()
    result.set_bands(result.get_bands()[:, slice_idx.get_list()])
    return result
