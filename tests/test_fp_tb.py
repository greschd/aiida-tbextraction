#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import pytest
import pymatgen
import numpy as np

from insb_sample import *

def test_fp_tb(
    configure_with_daemon,
    sample,
    get_fp_tb_input,
):
    from aiida.work import run
    from aiida.orm.querybuilder import QueryBuilder
    from aiida_bands_inspect.calculations.difference import DifferenceCalculation
    from aiida_tbextraction.work.first_principles_tb import FirstPrinciplesTbExtraction

    qb = QueryBuilder()
    qb.append(DifferenceCalculation)
    initial_count = qb.count()

    result = run(
        FirstPrinciplesTbExtraction,
        **get_fp_tb_input
    )
    print(result)
    assert all(key in result for key in ['cost_value', 'tb_model', 'window'])
    # check for the AiiDA locking bug (execute same step multiple times)
    assert qb.count() - initial_count <= 5 # there should be 5 valid windows
