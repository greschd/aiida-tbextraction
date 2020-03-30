# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for the band difference model evaluation workflow.
"""

import pymatgen
import numpy as np

from aiida import orm
from aiida.engine.launch import run_get_node

from aiida_tbextraction.model_evaluation import MaximumOrbitalDistanceEvaluation
from aiida_bands_inspect.io import read


def test_pos_distance_evaluation(
    configure_with_daemon,  # pylint: disable=unused-argument
    shared_datadir,
    silicon_structure
):
    """
    Run the model evaluation that gets the maximum distance between
    model orbitals and crystal positions.
    """
    builder = MaximumOrbitalDistanceEvaluation.get_builder()
    builder.code_tbmodels = orm.Code.get(label='tbmodels')

    builder.reference_structure = silicon_structure
    builder.reference_bands = read(shared_datadir / 'silicon' / 'bands.hdf5')

    with (shared_datadir / 'silicon' / 'model.hdf5').open('rb') as model_file:
        builder.tb_model = orm.SinglefileData(file=model_file)

    res, node = run_get_node(builder)
    assert np.isclose(res['cost_value'].value, 0.79, atol=0.01)
    assert node.is_finished_ok


def test_pos_distance_uc_not_matching(
    configure_with_daemon,  # pylint: disable=unused-argument
    shared_datadir
):
    """
    Test that passing a reference structure and tight-binding model
    which have non-matching unit cells raises the correct exit code.
    """
    builder = MaximumOrbitalDistanceEvaluation.get_builder()
    builder.code_tbmodels = orm.Code.get(label='tbmodels')

    structure = orm.StructureData()
    structure.set_pymatgen(
        pymatgen.Structure.from_file(
            shared_datadir / 'silicon' / 'si_uc_different.cif'
        )
    )
    builder.reference_structure = structure

    builder.reference_bands = read(shared_datadir / 'silicon' / 'bands.hdf5')

    with (shared_datadir / 'silicon' / 'model.hdf5').open('rb') as model_file:
        builder.tb_model = orm.SinglefileData(file=model_file)

    _, node = run_get_node(builder)
    assert node.is_finished
    assert node.exit_status == 300
    assert "unit cell" in node.exit_message
