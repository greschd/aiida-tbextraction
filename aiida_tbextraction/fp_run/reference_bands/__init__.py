# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Contains workflows for calculating the reference bandstructure with first-principles.
"""

from ._base import ReferenceBandsBase
from .._check_imports import HAS_QE, HAS_VASP

__all__ = ["ReferenceBandsBase"]

if HAS_QE:
    from ._qe import QuantumEspressoReferenceBands
    __all__.append("QuantumEspressoReferenceBands")
# if HAS_VASP:
#     from ._vasp import VaspReferenceBands
#     __all__.append("VaspReferenceBands")
