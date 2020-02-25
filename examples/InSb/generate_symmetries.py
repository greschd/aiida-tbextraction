#!/usr/bin/env python

# (c) 2017-2018, ETH Zurich, Institut fuer Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

import numpy as np
import pymatgen as mg
import pymatgen.symmetry.analyzer  # pylint: disable=unused-import
import symmetry_representation as sr

POS_In = (0, 0, 0)
POS_Sb = (0.25, 0.25, 0.25)

orbitals = []

for fct in sr.WANNIER_ORBITALS['s'] + sr.WANNIER_ORBITALS['p']:
    for spin in (sr.SPIN_UP, sr.SPIN_DOWN):
        orbitals.append(
            sr.Orbital(position=POS_In, function_string=fct, spin=spin)
        )
for fct in sr.WANNIER_ORBITALS['p']:
    for spin in (sr.SPIN_UP, sr.SPIN_DOWN):
        orbitals.append(
            sr.Orbital(position=POS_Sb, function_string=fct, spin=spin)
        )

structure = mg.Structure(
    lattice=[[0., 3.239, 3.239], [3.239, 0., 3.239], [3.239, 3.239, 0.]],
    species=['In', 'Sb'],
    coords=np.array([[0, 0, 0], [0.25, 0.25, 0.25]])
)

analyzer = mg.symmetry.analyzer.SpacegroupAnalyzer(structure)
symops = analyzer.get_symmetry_operations(cartesian=False)
symops_cart = analyzer.get_symmetry_operations(cartesian=True)

symmetry_group = sr.SymmetryGroup(
    symmetries=[
        sr.SymmetryOperation.from_orbitals(
            orbitals=orbitals,
            real_space_operator=sr.RealSpaceOperator.
            from_pymatgen(sym_reduced),
            rotation_matrix_cartesian=sym_cart.rotation_matrix,
            numeric=True
        ) for sym_reduced, sym_cart in zip(symops, symops_cart)
    ],
    full_group=True
)
time_reversal = sr.get_time_reversal(orbitals=orbitals, numeric=True)

sr.io.save([time_reversal, symmetry_group], 'inputs/symmetries.hdf5')
