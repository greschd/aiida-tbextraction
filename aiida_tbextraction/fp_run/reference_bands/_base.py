# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the base class for workflows that calculate the reference bandstructure.
"""

from aiida import orm
from aiida.engine import WorkChain

__all__ = ('ReferenceBandsBase', )


class ReferenceBandsBase(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the reference bandstructure. It defines the inputs required by these WorkChains.
    """
    @classmethod
    def define(cls, spec):
        super().define(spec)

        spec.input(
            'structure',
            valid_type=orm.StructureData,
            help='Structure of the material.'
        )
        spec.input(
            'kpoints',
            valid_type=orm.KpointsData,
            help='k-points on which the bandstructure is evaluated.'
        )

        spec.output(
            'bands',
            valid_type=orm.BandsData,
            help='The reference bandstructure.'
        )
