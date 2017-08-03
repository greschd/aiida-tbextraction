#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida.orm import DataFactory
from aiida.orm.code import Code
from aiida.orm.data.base import List
from .base import ReferenceBandsBase

class VaspHybridsBands(ReferenceBandsBase):
    """
    The WorkChain to calculate reference bands with VASP, using hybrids.
    """
    @classmethod
    def define(cls, spec):
        super(VaspHybridsBands, cls).define(spec)

        spec.outline()
