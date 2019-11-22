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
def band_difference_builder(configure, sample):  # pylint: disable=unused-argument
    """
    Create inputs for the band difference workflow.
    """
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
    from aiida_bands_inspect.io import read_bands

    builder = BandDifferenceModelEvaluation.get_builder()
    builder.tbmodels_code = orm.Code.get_from_string('tbmodels')
    builder.bands_inspect_code = orm.Code.get_from_string('bands_inspect')
    builder.tb_model = orm.SinglefileData(file=sample('silicon/model.hdf5'))
    builder.reference_bands = read_bands(sample('silicon/bands.hdf5'))

    return builder


@pytest.mark.skip("Not yet migrated.")
def test_bandevaluation(configure_with_daemon, band_difference_builder):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Run the band evaluation workflow.
    """
    from aiida.engine.launch import run
    builder = band_difference_builder
    output = run(builder)
    assert np.isclose(output['cost_value'].value, 0.)
