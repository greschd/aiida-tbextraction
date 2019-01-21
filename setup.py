# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>
"""
Usage: pip install .[dev]
"""

import re
from setuptools import setup, find_packages

# Get the version number
with open('./aiida_tbextraction/__init__.py') as f:
    MATCH_EXPR = "__version__[^'\"]+(['\"])([^'\"]+)"
    VERSION = re.search(MATCH_EXPR, f.read()).group(2).strip()

if __name__ == '__main__':
    setup(
        name='aiida-tbextraction',
        version=VERSION,
        description='AiiDA Plugin for extracting tight-binding models',
        author='Dominik Gresch',
        author_email='greschd@gmx.ch',
        license='Apache 2.0',
        classifiers=[
            'Development Status :: 3 - Alpha', 'Environment :: Plugins',
            'Framework :: AiiDA', 'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3.6',
            'Topic :: Scientific/Engineering :: Physics'
        ],
        keywords='tight-binding extraction aiida workflows',
        packages=find_packages(exclude=['aiida']),
        include_package_data=True,
        setup_requires=['reentry'],
        reentry_register=True,
        install_requires=[
            'aiida-core', 'aiida-wannier90', 'aiida-bands-inspect',
            'aiida-tbmodels', 'aiida-optimize', 'fsc.export', 'aiida-tools',
            'future'
        ],
        extras_require={
            ':python_version < "3"': ['chainmap', 'singledispatch'],
            'dev': [
                'pymatgen', 'aiida-pytest', 'ase', 'yapf==0.19', 'pre-commit',
                'sphinx-rtd-theme', 'sphinx-pyreverse'
            ],
            'strain': ['aiida-strain'],
            'vasp': ['aiida-vasp'],
        },
        entry_points={},
    )
