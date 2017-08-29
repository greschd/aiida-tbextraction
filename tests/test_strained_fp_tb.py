#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools

import pytest
import pymatgen
import numpy as np

from insb_sample import *

def test_strained_fp_tb(
    configure_with_daemon,
    sample,
    get_fp_tb_input,
):
    from aiida.work import run
    from aiida.orm.code import Code
    from aiida.orm.data.base import Str, List
    from aiida_tbextraction.work.strained_fp_tb import StrainedFpTbExtraction
    inputs = get_fp_tb_input

    inputs['strain_kind'] = Str('three_five.Biaxial001')
    inputs['strain_parameters'] = Str('InSb')

    strain_strengths = List()
    strain_list = [-0.1, 0., 0.1]
    strain_strengths.extend(strain_list)
    inputs['strain_strengths'] = strain_strengths

    inputs['symmetry_repr_code'] = Code.get_from_string('symmetry_repr')

    result = run(
        StrainedFpTbExtraction,
        **inputs
    )
    print(result)
    for value in strain_list:
        suffix = '_{}'.format(value)
        assert all(key + suffix in result for key in ['cost_value', 'tb_model', 'window'])
