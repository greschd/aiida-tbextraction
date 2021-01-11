# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Workflows for running the first-principles calculations needed as input for the tight-binding calculation and evaluation.
"""

import contextlib

from ._base import FirstPrinciplesRunBase
from ._check_imports import HAS_QE, HAS_VASP

__all__ = ["FirstPrinciplesRunBase"]

if HAS_QE:
    from ._qe_run import QuantumEspressoFirstPrinciplesRun
    __all__.append("QuantumEspressoFirstPrinciplesRun")
# if HAS_VASP:
#     from ._vasp_run import VaspFirstPrinciplesRun
#     __all__.append("VaspFirstPrinciplesRun")
