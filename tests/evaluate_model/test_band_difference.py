"""
Tests for the band difference model evaluation workflow.
"""

from __future__ import division, print_function, unicode_literals

import pytest
import numpy as np


@pytest.fixture
def band_difference_process_inputs(configure, sample):  # pylint: disable=unused-argument
    """
    Create inputs for the band difference workflow.
    """
    from aiida.orm import DataFactory
    from aiida.orm.code import Code
    from aiida_tbextraction.model_evaluation import BandDifferenceModelEvaluation
    from aiida_bands_inspect.io import read_bands

    inputs = BandDifferenceModelEvaluation.get_inputs_template()
    inputs.tbmodels_code = Code.get_from_string('tbmodels')
    inputs.bands_inspect_code = Code.get_from_string('bands_inspect')
    inputs.tb_model = DataFactory('singlefile')(
        file=sample('silicon/model.hdf5')
    )
    inputs.reference_bands = read_bands(sample('silicon/bands.hdf5'))

    return BandDifferenceModelEvaluation, inputs


def test_bandevaluation(configure_with_daemon, band_difference_process_inputs):  # pylint: disable=unused-argument,redefined-outer-name
    """
    Run the band evaluation workflow.
    """
    from aiida.work import run
    process, inputs = band_difference_process_inputs
    output = run(process, **inputs)
    assert np.isclose(output['cost_value'].value, 0.)


def test_bandevaluation_launchmany(
    configure_with_daemon,  # pylint: disable=unused-argument
    band_difference_process_inputs,  # pylint: disable=redefined-outer-name
    wait_for
):
    """
    Launch many band evaluation workflows, and check that the right number of workflows was executed.
    """
    from aiida.work import submit
    from aiida.orm import CalculationFactory
    from aiida.orm.querybuilder import QueryBuilder
    qb1 = QueryBuilder()
    qb2 = QueryBuilder()
    qb1.append(CalculationFactory('tbmodels.eigenvals'))
    qb2.append(CalculationFactory('bands_inspect.difference'))

    initial_count1 = qb1.count()
    initial_count2 = qb2.count()
    num_workflows = 100

    process, inputs = band_difference_process_inputs
    pids = []
    for _ in range(num_workflows):
        pids.append(submit(process, **inputs).pid)

    for process_id in pids:
        wait_for(process_id)

    end_count1 = qb1.count()
    end_count2 = qb2.count()
    assert end_count1 - initial_count1 == num_workflows
    assert end_count2 - initial_count2 == num_workflows
