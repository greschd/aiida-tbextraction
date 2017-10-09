Workflows to run DFT calculations
=================================

Workflows to run all necessary DFT calculations
-----------------------------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.base.RunDFTBase

.. aiida-workchain:: aiida_tbextraction.run_dft.split_runs.SplitDFTRuns

Reference Bands Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.reference_bands.base.ReferenceBandsBase

.. aiida-workchain:: aiida_tbextraction.run_dft.reference_bands.vasp_hybrids.VaspHybridsBands


Wannier90 Input Workflows
-------------------------

.. aiida-workchain:: aiida_tbextraction.run_dft.wannier_input.base.ToWannier90Base

.. aiida-workchain:: aiida_tbextraction.run_dft.wannier_input.vasp.VaspToWannier90
