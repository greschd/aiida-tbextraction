# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Contains workflows for calculating the reference bandstructure with first-principles.
"""

from ._base import ReferenceBandsBase

__all__ = _base.__all__  # pylint: disable=undefined-variable

try:
    from ._vasp import VaspReferenceBands
    __all__ += _vasp.__all__  # pylint: disable=undefined-variable
except ImportError:
    pass
