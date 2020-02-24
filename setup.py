# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Usage: pip install .[dev]
"""

import os
import json
from setuptools import setup, find_packages

SETUP_JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'setup.json'
)
with open(SETUP_JSON_PATH, 'r') as json_file:
    SETUP_KWARGS = json.load(json_file)

EXTRAS_REQUIRE = SETUP_KWARGS['extras_require']
# sphinx needs to be able to import these requirements
EXTRAS_REQUIRE['docs'] += EXTRAS_REQUIRE['qe'] + EXTRAS_REQUIRE['strain']
# define a "full" development install
EXTRAS_REQUIRE['dev'] = (
    EXTRAS_REQUIRE['testing'] + EXTRAS_REQUIRE['docs'] +
    EXTRAS_REQUIRE['dev_precommit']
)

if __name__ == '__main__':
    setup(packages=find_packages(exclude=['aiida']), **SETUP_KWARGS)
