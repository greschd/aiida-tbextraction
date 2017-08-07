#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.base import List
from aiida.work.workchain import WorkChain

class ToWannier90Base(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the Wannier90 input files. It defines the inputs required by these WorkChains.
    """
    @classmethod
    def define(cls, spec):
        super(ToWannier90Base, cls).define(spec)

        ParameterData = DataFactory('parameter')
        spec.input('structure', valid_type=DataFactory('structure'))
        spec.input('kpoints_mesh', valid_type=DataFactory('array.kpoints'))
        spec.input_group('potentials')
        spec.input('code', valid_type=Code)
        spec.input('parameters', valid_type=ParameterData)
        spec.input('calculation_kwargs', valid_type=ParameterData)

        spec.input(
            'wannier_parameters', valid_type=ParameterData,
            required=False
        )
        spec.input(
            'wannier_projections',
            valid_type=(DataFactory('orbital'), List), required=False
        )

        spec.output(
            'wannier_input_folder', valid_type=DataFactory('folder')
        )
