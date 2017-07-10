#!/usr/bin/env python
# -*- coding: utf-8 -*-

from ._utils import create_workchain

_workchain_template = """\
from aiida.orm.data.base import Int
from aiida.work.workchain import WorkChain

class {typename}(WorkChain):
    @classmethod
    def define(cls, spec):
        super({typename}, cls).define(spec)
        spec.outline(cls.test)

    def test(self):
        self.out('test', Int({output}))
"""


TestOne = create_workchain('TestOne', _workchain_template, output=1)
TestTwo = create_workchain('TestTwo', _workchain_template, output=2)
