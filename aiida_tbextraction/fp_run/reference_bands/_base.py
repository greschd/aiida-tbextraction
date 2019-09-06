# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the base class for workflows that calculate the reference bandstructure.
"""

from fsc.export import export

from aiida.plugins import DataFactory
from aiida.engine import WorkChain


@export
class ReferenceBandsBase(WorkChain):
    """
    The base class for WorkChains which can be used to calculate the reference bandstructure. It defines the inputs required by these WorkChains.
    """

    @classmethod
    def define(cls, spec):
        super(ReferenceBandsBase, cls).define(spec)

        spec.input(
            'structure',
            valid_type=DataFactory('structure'),
            help='Structure of the material.'
        )
        spec.input(
            'kpoints',
            valid_type=DataFactory('array.kpoints'),
            help='k-points on which the bandstructure is evaluated.'
        )
        spec.input(
            'kpoints_mesh',
            valid_type=DataFactory('array.kpoints'),
            required=False,
            help=
            'k-point mesh used to perform the initial convergence. This is needed e.g. for VASP hybrids calculations.'
        )
        spec.input_namespace(
            'potentials',
            dynamic=True,
            help='Pseudopotentials used in the calculation.'
        )

        spec.output(
            'bands',
            valid_type=DataFactory('array.bands'),
            help='The reference bandstructure.'
        )
