# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests the workflow which calculates the tight-binding model from a complete Wannier90 input folder and symmetry + slice inputs.
"""

import os
import itertools

import pytest
import pymatgen
import numpy as np

from aiida import orm
from aiida.engine import run_get_node

from aiida_tbextraction.calculate_tb import TightBindingCalculation


@pytest.mark.parametrize('slice_', [True, False])
@pytest.mark.parametrize('symmetries', [True, False])
def test_tbextraction(
    configure_with_daemon, test_data_dir, slice_, symmetries, code_wannier90
):  # pylint: disable=unused-argument
    """
    Run the tight-binding calculation workflow, optionally including symmetrization and slicing of orbitals.
    """

    builder = TightBindingCalculation.get_builder()

    wannier_input_folder = orm.FolderData()
    wannier_input_folder_path = test_data_dir / 'wannier_input_folder'
    for filename in os.listdir(wannier_input_folder_path):
        wannier_input_folder.put_object_from_file(
            str((wannier_input_folder_path / filename).resolve()), filename
        )
    builder.wannier.local_input_folder = wannier_input_folder

    builder.wannier.code = code_wannier90

    builder.code_tbmodels = orm.Code.get_from_string('tbmodels')

    k_values = [
        x if x <= 0.5 else -1 + x
        for x in np.linspace(0, 1, 6, endpoint=False)
    ]
    k_points = [
        list(reversed(k)) for k in itertools.product(k_values, repeat=3)
    ]
    wannier_kpoints = orm.KpointsData()
    wannier_kpoints.set_kpoints(k_points)
    builder.wannier.kpoints = wannier_kpoints

    a = 3.2395  # pylint: disable=invalid-name
    structure = orm.StructureData()
    structure.set_pymatgen_structure(
        pymatgen.Structure(
            lattice=[[0, a, a], [a, 0, a], [a, a, 0]],
            species=['In', 'Sb'],
            coords=[[0] * 3, [0.25] * 3]
        )
    )
    builder.structure = structure

    builder.wannier.parameters = orm.Dict(
        dict=dict(
            num_wann=14,
            num_bands=36,
            dis_num_iter=1000,
            num_iter=0,
            dis_win_min=-4.5,
            dis_win_max=16.,
            dis_froz_min=-4,
            dis_froz_max=6.5,
            spinors=True,
            mp_grid=[6, 6, 6]
        )
    )
    builder.wannier.metadata.options = {
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 1
        },
        'withmpi': False
    }
    if symmetries:
        # This is needed because otherwise the symmetrization doesn't work
        builder.parse.calc.distance_ratio_threshold = orm.Float(2.)

        builder.symmetries = orm.SinglefileData(
            file=str(test_data_dir / 'symmetries.hdf5')
        )
    if slice_:
        slice_idx = orm.List()
        slice_idx.extend([0, 2, 3, 1, 5, 6, 4, 7, 9, 10, 8, 12, 13, 11])
        builder.slice_idx = slice_idx

    result, node = run_get_node(builder)
    assert node.is_finished_ok
    assert 'tb_model' in result
