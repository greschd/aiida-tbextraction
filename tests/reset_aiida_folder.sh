# -*- coding: utf-8 -*-

# © 2017-2019, ETH Zurich, Institut für Theoretische Physik
# Author: Dominik Gresch <greschd@gmx.ch>

if [ -d .aiida~ ]; then
    rm -r .aiida
    mv .aiida~ .aiida
fi
