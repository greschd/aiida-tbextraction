#!/bin/bash

# Author: Dominik Gresch <greschd@gmx.ch>

# Be verbose, and stop with error as soon there's one
set -ev

pip install -U 'pip<19' wheel setuptools
pip install git+https://github.com/greschd/aiida-wannier90.git@edge

cd ${TRAVIS_BUILD_DIR}

case "$INSTALL_TYPE" in
    testing)
        pip install .[testing,strain]
        ;;
    testing_sdist)
        python setup.py sdist
        ls -1 dist/ | xargs -I % pip install dist/%[testing,strain]
        ;;
    dev_precommit)
        pip install .[dev_precommit,strain]
        ;;
esac

reentry scan
