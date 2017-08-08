#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida_pytest import *
from aiida_pytest import pytest_addoption as _addoption
import pytest

def pytest_addoption(parser):
    parser.addoption('--queue-name', action='store', default='express_compute', help='Name of the queue used to submit calculations.')
    _addoption(parser)

@pytest.fixture
def queue_name(request):
    return request.config.getoption('--queue-name')
