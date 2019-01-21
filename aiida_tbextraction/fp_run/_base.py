# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Defines the base class for workflows that run the first-principles calculations.
"""

from fsc.export import export

from aiida.work.workchain import WorkChain

from .reference_bands import ReferenceBandsBase
from .wannier_input import WannierInputBase


@export
class FirstPrinciplesRunBase(WorkChain):
    """
    Base class for first-principles runs, calculation the reference bandstructure and Wannier90 inputs.
    """

    @classmethod
    def define(cls, spec):
        super(FirstPrinciplesRunBase, cls).define(spec)

        spec.expose_inputs(ReferenceBandsBase)
        spec.expose_inputs(WannierInputBase)

        spec.expose_outputs(ReferenceBandsBase)
        spec.expose_outputs(WannierInputBase)
