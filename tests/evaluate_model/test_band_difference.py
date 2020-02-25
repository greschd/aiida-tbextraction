# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Tests for the band difference model evaluation workflow.
"""

import pytest
import numpy as np

from aiida import orm


@pytest.fixture
def band_difference_builder(configure, shared_datadir):  # pylint: disable=unused-argument
    """
    Create inputs for the band difference workflow.
    """
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
    from aiida_bands_inspect.io import read_bands

    builder = BandDifferenceModelEvaluation.get_builder()
    builder.code_tbmodels = orm.Code.get_from_string('tbmodels')
    builder.code_bands_inspect = orm.Code.get_from_string('bands_inspect')
    with (shared_datadir / 'silicon/model.hdf5').open('rb') as model_file:
        builder.tb_model = orm.SinglefileData(file=model_file)
    builder.reference_bands = read_bands(shared_datadir / 'silicon/bands.hdf5')

    return builder


def test_bandevaluation(configure_with_daemon, band_difference_builder):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Run the band evaluation workflow.
    """
    from aiida.engine.launch import run
    builder = band_difference_builder
    output = run(builder)
    assert np.isclose(output['cost_value'].value, 0.)
