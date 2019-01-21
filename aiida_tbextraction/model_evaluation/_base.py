# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the base class for workflows that evaluate a tight-binding model.
"""

from fsc.export import export

from aiida.work.workchain import WorkChain
from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.base import Float


@export
class ModelEvaluationBase(WorkChain):
    """
    Base class for evaluating a tight-binding model. The workflow returns a cost measure, which should be minimized to get an optimal model.
    """

    @classmethod
    def define(cls, spec):
        super(ModelEvaluationBase, cls).define(spec)
        spec.input(
            'tb_model',
            valid_type=DataFactory('singlefile'),
            help='Tight-binding model to be evaluated, in TBmodels HDF5 format.'
        )
        spec.input(
            'reference_bands',
            valid_type=DataFactory('array.bands'),
            help='Bandstructure of the reference model.'
        )
        spec.input(
            'tbmodels_code',
            valid_type=Code,
            help='Code that runs the TBmodels CLI.'
        )

        spec.output('cost_value', valid_type=Float)
