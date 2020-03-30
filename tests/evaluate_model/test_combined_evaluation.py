# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for the band difference model evaluation workflow.
"""

import numpy as np

from aiida import orm
from aiida.engine.launch import run_get_node

from aiida_tbextraction.model_evaluation import CombinedEvaluation, BandDifferenceModelEvaluation
from aiida_bands_inspect.io import read


def test_combined_evaluation(
    configure_with_daemon,  # pylint: disable=unused-argument
    shared_datadir,
    silicon_structure
):
    """
    Run the combined evaluation workflow by using the band difference
    evaluation twice.
    """
    builder = CombinedEvaluation.get_builder()
    builder.code_tbmodels = orm.Code.get(label='tbmodels')

    builder.reference_structure = silicon_structure

    builder.reference_bands = read(shared_datadir / 'silicon' / 'bands.hdf5')

    with (shared_datadir / 'silicon' / 'model.hdf5').open('rb') as model_file:
        builder.tb_model = orm.SinglefileData(file=model_file)

    extra_inputs = {
        'code_bands_inspect': orm.Code.get_from_string('bands_inspect')
    }
    builder.extra_inputs = {'eval1': extra_inputs, 'eval2': extra_inputs}
    builder.labels = orm.List(list=['eval1', 'eval2'])
    builder.process_classes = [
        BandDifferenceModelEvaluation, BandDifferenceModelEvaluation
    ]
    builder.weights = orm.List(list=[1., 2.])

    res, node = run_get_node(builder)
    assert np.isclose(res['cost_value'].value, 0.)
    assert node.is_finished_ok
    assert 'cost_value' in res['extra_outputs']['eval1']
    assert 'cost_value' in res['extra_outputs']['eval2']
    assert 'plot' in res['extra_outputs']['eval1']
    assert 'plot' in res['extra_outputs']['eval2']
