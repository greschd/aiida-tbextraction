Workflows to run DFT calculations
=================================

Workflows to run all necessary DFT calculations
-----------------------------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.RunDFTBase

.. aiida-workchain:: aiida_tbextraction.run_dft.split_runs.SplitRunDFT

Reference Bands Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.reference_bands.ReferenceBandsBase

.. aiida-workchain:: aiida_tbextraction.run_dft.reference_bands.vasp_hybrids.VaspHybridsBands


Wannier90 Input Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.wannier_input.WannierInputBase

.. aiida-workchain:: aiida_tbextraction.run_dft.wannier_input.vasp.VaspWannierInputBase
