# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Contains workflows for calculating the Wannier90 input files with first-principles.
"""

from ._base import WannierInputBase
from .._check_imports import HAS_QE, HAS_VASP

__all__ = ["WannierInputBase"]

if HAS_QE:
    from ._qe import QuantumEspressoWannierInput
    __all__.append("QuantumEspressoWannierInput")
# if HAS_VASP:
#     from ._vasp import VaspWannierInput
#     __all__.append("VaspWannierInput")
