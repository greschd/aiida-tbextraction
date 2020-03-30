# -*- coding: utf-8 -*-
"""
Pytest configuration for the model evaluation tests.
"""

import pytest
import pymatgen

from aiida import orm


@pytest.fixture
def silicon_structure(configure):  # pylint: disable=unused-argument
    """Returns a StructureData for silicon."""
    struc = orm.StructureData()
    struc.set_pymatgen(
        pymatgen.Structure(
            lattice=[[-2.6988, 0, 2.6988], [0, 2.6988, 2.6988],
                     [-2.6988, 2.6988, 0]],
            species=['Si', 'Si'],
            coords=[[-0.25, 0.75, -0.25], [0, 0, 0]]
        )
    )
    return struc
