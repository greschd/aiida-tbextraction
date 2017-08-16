# -*- coding: utf-8 -*-

import re
from setuptools import setup, find_packages

# Get the version number
with open('./aiida_tbextraction/__init__.py') as f:
    match_expr = "__version__[^'\"]+(['\"])([^'\"]+)"
    version = re.search(match_expr, f.read()).group(2).strip()

if __name__ == '__main__':
    setup(
        name='aiida-tbextraction',
        version=version,
        description='AiiDA Plugin for extracting tight-binding models',
        author='Dominik Gresch',
        author_email='greschd@gmx.ch',
        license='MIT',
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Plugins',
            'Framework :: AiiDA',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2.7',
            'Topic :: Scientific/Engineering :: Physics'
        ],
        keywords='tight-binding extraction aiida workflows',
        packages=find_packages(exclude=['aiida']),
        include_package_data=True,
        setup_requires=[
            'reentry'
        ],
        reentry_register=True,
        install_requires=[
            'aiida-core',
            'aiida-vasp',
            'aiida-wannier90',
            'aiida-bands-inspect',
            'aiida-tbmodels',
            'chainmap',
            'singledispatch'
        ],
        extras_require={
            'test': ['pymatgen', 'aiida-pytest', 'ase']
        },
        entry_points={
        },
    )
