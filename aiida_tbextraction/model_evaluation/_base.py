# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the base class for workflows that evaluate a tight-binding model.
"""

from aiida import orm
from aiida.engine import WorkChain

__all__ = ('ModelEvaluationBase', )


class ModelEvaluationBase(WorkChain):
    """
    Base class for evaluating a tight-binding model. The workflow returns a cost measure, which should be minimized to get an optimal model.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input(
            'tb_model',
            valid_type=orm.SinglefileData,
            help='Tight-binding model to be evaluated, in TBmodels HDF5 format.'
        )
        spec.input(
            'reference_bands',
            valid_type=orm.BandsData,
            help='Bandstructure of the reference model.'
        )
        spec.input(
            'code_tbmodels',
            valid_type=orm.Code,
            help='Code that runs the TBmodels CLI.'
        )

        spec.output('cost_value', valid_type=orm.Float)
