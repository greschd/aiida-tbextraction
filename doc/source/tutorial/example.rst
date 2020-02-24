.. © 2017-2019, ETH Zurich, Institut für Theoretische Physik
.. Author: Dominik Gresch <greschd@gmx.ch>

Example Calculation
===================

The easiest way to get started with ``aiida-tbextraction`` is by modifying an existing example. For this reason, we will describe such an example here.

Workflow Structure
------------------

The following diagram shows the structure of the :class:`.OptimizeFirstPrinciplesTightBinding` workflow. In a first step, the first-principles workflow is called to create the necessary inputs for the Wannier90 calculations. Next, the :class:`.WindowSearch` workflow is called, which runs an optimization (using ``aiida-optimize``) for the energy windows. The individual calculations are carried out by the :class:`.RunWindow` workflow, which is shown in the second part of the diagram.

First, the :class:`.RunWindow` workflow calculates the tight-binding model using the :class:`.TightBindingCalculation` workflow. This runs Wannier90, and then parses the output to the TBmodels HDF5 format. If requested, the model is also sliced and symmetrized. Then, the resulting tight-binding model is evaluated using a subclass of the :class:`.ModelEvaluationBase` workflow. This workflow assigns a "cost value" to the tight-binding model, which is a measure for the quality (lower is better) of the model. The cost value is what's used by the optimization workflow to find the optimal energy windows.

|

.. image:: images/workflow_diagram.svg
    :width: 504px
    :align: center
    :alt: Optimization workflow diagram

|

The workflow which runs the first-principles calculations can be different depending on which code you would like to run. Currently, only Quantum ESPRESSO is supported by default, with the :class:`.QuantumEspressoFirstPrinciplesRun` workflow. It first runs an SCF calculation, and then uses the :class:`.QuantumEspressoReferenceBands` and :class:`.QuantumEspressoWannierInput` workflows to calculate the reference band structure and Wannier90 input files, respectively.


Launching the Workflow
----------------------

The following example runs a simple tight-binding calculation for InSb. It builds up the required inputs step by step, using a process builder. To test that your setup has worked correctly, you can try launching this example. The code is also available on `GitHub <https://github.com/greschd/aiida-tbextraction>`_. You will have to adjust some values specific to your configuration, like the queue name on the compute cluster or the names of the codes.

Once you have successfully ran this example, you can start adapting it to your use case. The :ref:`Reference <optimize_fp_tb_reference>` section can help you understand the individual input values. For production runs, you should decrease the tolerances ``window_tol`` and ``cost_tol`` (or use their default values), and use more accurate inputs for the DFT and Wannier calculations (for example, you should increase ``dis_num_iter``).

.. include:: ../../../examples/InSb/run_optimization.py
    :code: python

Note that the result of this example does not accurately represent the band-structure of InSb. This is due to the limitation of PBE, and could be overcome by using costlier hybrid functional calculations.

.. note ::

    Using hybrid functionals is currently not supported in the :class:`.QuantumEspressoFirstPrinciplesRun` workflow, due to limitations in QE itself.


Customizing the workflow
------------------------

There are different ways in which you can customize the tight-binding extraction workflow to match your use case. If you already have the output from a first-principles calculation, you can directly use either the :class:`.WindowSearch`, :class:`.RunWindow` or :class:`.TightBindingCalculation` workflow, depending on which features you want to run. Also, you could change the workflow which is uded to run the first-principles calculations. When implementing such a workflow, you should make sure that it adheres to the interface defined in :class:`.FirstPrinciplesRunBase`, meaning that it should take *at least* the inputs defined there, and create the corresponding outputs. The easiest way to do this is by inheriting from the base class. The workflow can take *additional* inputs, which you can pass through the ``fp_run`` namespace in the :class:`.OptimizeFirstPrinciplesTightBinding` workflow inputs. Finally, you can also use a different workflow for *evaluating* the tight-binding model. This allows you to create a measure for the quality of the model which fits best to your specific use case.
