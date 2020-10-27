# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for the band difference model evaluation workflow.
"""

import pytest
import numpy as np

from aiida import orm
from aiida.engine.launch import run_get_node, submit

from aiida_tbextraction.model_evaluation import CombinedEvaluation, BandDifferenceModelEvaluation
from aiida_bands_inspect.io import read


@pytest.fixture
def get_combined_evaluation_builder(
    configure,  # pylint: disable=unused-argument
    shared_datadir,
    silicon_structure
):
    """
    Fixture to create a builder for the combined evaluation workflow.
    """
    def _get_combined_evaluation_builder():
        builder = CombinedEvaluation.get_builder()
        builder.code_tbmodels = orm.Code.get(label='tbmodels')

        builder.reference_structure = silicon_structure

        builder.reference_bands = read(
            shared_datadir / 'silicon' / 'bands.hdf5'
        )

        with (shared_datadir / 'silicon' /
              'model.hdf5').open('rb') as model_file:
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
        return builder

    return _get_combined_evaluation_builder


def test_combined_evaluation(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_combined_evaluation_builder  # pylint: disable=redefined-outer-name
):
    """
    Run the combined evaluation workflow by using the band difference
    evaluation twice.
    """
    builder = get_combined_evaluation_builder()
    res, node = run_get_node(builder)
    assert np.isclose(res['cost_value'].value, 0.)
    assert node.is_finished_ok
    assert 'cost_value' in res['extra_outputs']['eval1']
    assert 'cost_value' in res['extra_outputs']['eval2']
    assert 'plot' in res['extra_outputs']['eval1']
    assert 'plot' in res['extra_outputs']['eval2']


def test_combined_evaluation_submit(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_combined_evaluation_builder,  # pylint: disable=redefined-outer-name
    wait_for
):
    """
    Run the combined evaluation workflow by using the band difference
    evaluation twice.
    """
    builder = get_combined_evaluation_builder()
    node = submit(builder)
    wait_for(node.pk)
    res = node.outputs
    assert np.isclose(res['cost_value'].value, 0.)
    assert node.is_finished_ok
    assert 'extra_outputs__eval1__cost_value' in res
    assert 'extra_outputs__eval2__cost_value' in res
    assert 'extra_outputs__eval1__plot' in res
    assert 'extra_outputs__eval2__plot' in res
