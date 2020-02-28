#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Helper module to check which of the possible DFT code plugins are
available.
"""

__all__ = ("HAS_QE", "HAS_VASP")

try:
    import aiida_quantumespresso  # pylint: disable=unused-import
except ImportError:
    HAS_QE = False
else:
    HAS_QE = True

try:
    import aiida_vasp  # pylint: disable=unused-import
except ImportError:
    HAS_VASP = False
else:
    HAS_VASP = True
