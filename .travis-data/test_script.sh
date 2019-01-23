#!/bin/bash
# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

# Be verbose, and stop with error as soon there's one
set -ev

case "$TEST_TYPE" in
    tests)
        # Run the AiiDA tests
        cd ${TRAVIS_BUILD_DIR}/.travis-data; ./build_wannier90.sh
        python ${TRAVIS_BUILD_DIR}/.travis-data/configure.py ${TRAVIS_BUILD_DIR}/.travis-data ${TRAVIS_BUILD_DIR}/.travis-data/test_config.yml ${TRAVIS_BUILD_DIR}/tests/config.yml;
        export AIIDA_PATH="${TRAVIS_BUILD_DIR}/tests"
        cd ${TRAVIS_BUILD_DIR}/tests; pytest --skip-vasp --quiet-wipe --print-status
        ;;
    pre-commit)
        pre-commit run --all-files
        ;;
esac
