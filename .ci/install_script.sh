#!/bin/bash

# Author: Dominik Gresch <greschd@gmx.ch>

# Be verbose, and stop with error as soon there's one
set -ev

pip install -U pip wheel setuptools

case "$INSTALL_TYPE" in
    testing)
        pip install .[testing,strain]
        ;;
    testing_sdist)
        python setup.py sdist
        ls -1 dist/ | xargs -I % pip install dist/%[testing,strain]
        ;;
    dev_precommit)
        pip install .[dev]
        ;;
    docs)
        pip install .[docs]
        ;;
esac

reentry scan
