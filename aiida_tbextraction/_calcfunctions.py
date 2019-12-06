# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines helper inline calculations.
"""

from multipledispatch import dispatch

from aiida import orm
from aiida.engine import calcfunction

__all__ = ('merge_nested_dict', 'slice_bands_inline')


@calcfunction
def slice_bands_inline(bands, slice_idx):
    """
    Slices the given BandsData such that only the bands given in ``slice_idx``
    remain, in the given order.  The k-points remain unchanged.
    """
    result = bands.clone()
    result.set_bands(result.get_bands()[:, slice_idx.get_list()])
    return result


@calcfunction
def merge_nested_dict(dict_primary, dict_secondary):
    """
    Merges two (possibly nested) Dict objects, giving precedence to the primary.
    """
    return orm.Dict(
        dict=_merge(dict_primary.get_dict(), dict_secondary.get_dict())
    )


@dispatch(object, object)
def _merge(obj1, obj2):  # pylint: disable=unused-argument
    return obj1


@dispatch(type(None), object)  # type: ignore
def _merge(obj1, obj2):  # pylint: disable=unused-argument
    return obj2


@dispatch(dict, dict)  # type: ignore
def _merge(dict1, dict2):  # pylint: disable=missing-docstring
    res = {}
    res.update(dict2)
    res.update(dict1)
    key_intersection = set(dict1.keys()).intersection(dict2.keys())
    for key in key_intersection:
        res[key] = _merge(dict1[key], dict2[key])
    return res
