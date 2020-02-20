.. © 2017-2019, ETH Zurich, Institut für Theoretische Physik
.. Author: Dominik Gresch <greschd@gmx.ch>

Run First-Principles Calculations
=================================

Complete First-Principles Calculations
--------------------------------------

.. aiida-workchain:: FirstPrinciplesRunBase
    :module: aiida_tbextraction.fp_run

.. aiida-workchain:: QuantumEspressoFirstPrinciplesRun
    :module: aiida_tbextraction.fp_run

Reference Bands Workflows
-------------------------

.. automodule:: aiida_tbextraction.fp_run.reference_bands
    :members:

Wannier90 Input Workflows
-------------------------

.. automodule:: aiida_tbextraction.fp_run.wannier_input
    :members:
