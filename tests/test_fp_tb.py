"""
Test for the workflow that optimizes DFT-based tight-binding models.
"""

from __future__ import print_function

from insb_sample import get_fp_tb_input  # pylint: disable=unused-import


def test_fp_tb(
    configure_with_daemon,  # pylint: disable=unused-argument
    get_fp_tb_input,  # pylint: disable=redefined-outer-name
):
    """
    Runs the DFT tight-binding optimization workflow on an InSb sample.
    """
    from aiida.work import run
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.first_principles_tb import FirstPrinciplesTbExtraction

    query = QueryBuilder()
    query.append(DifferenceCalculation)
    initial_count = query.count()

    result = run(FirstPrinciplesTbExtraction, **get_fp_tb_input)
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])
    # check for the AiiDA locking bug (execute same step multiple times)
    assert query.count() - initial_count <= 5  # there should be 5 valid windows
