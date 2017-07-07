#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

@pytest.mark.parametrize('slice', [True, False])
@pytest.mark.parametrize('symmetries', [True, False])
def test_runwindow(configure_with_daemon, sample, slice, symmetries):
    from aiida_tbextraction.work.runwindow import RunWindow
    
