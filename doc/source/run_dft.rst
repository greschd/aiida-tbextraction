Workflows to run DFT calculations
=================================

Workflows to run all necessary DFT calculations
-----------------------------------------------

.. aiida-workchain:: aiida_tbextraction.dft_run.DFTRunBase

.. aiida-workchain:: aiida_tbextraction.dft_run.split_runs.SplitDFTRun

Reference Bands Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.dft_run.reference_bands.ReferenceBandsBase

.. aiida-workchain:: aiida_tbextraction.dft_run.reference_bands.vasp_hybrids.VaspHybridsBands


Wannier90 Input Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.dft_run.wannier_input.WannierInputBase

.. aiida-workchain:: aiida_tbextraction.dft_run.wannier_input.vasp.VaspWannierInputBase
