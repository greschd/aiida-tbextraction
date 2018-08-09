"""
Contains workflows for calculating the Wannier90 input files with first-principles.
"""

from ._base import WannierInputBase

__all__ = _base.__all__  # pylint: disable=undefined-variable
try:
    from ._vasp import VaspWannierInput
    __all__ += _vasp.__all__  # pylint: disable=undefined-variable
except ImportError:
    pass
