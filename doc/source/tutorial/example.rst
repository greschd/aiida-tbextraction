Example Calculation
===================

The easiest way to get started with ``aiida-tbextraction`` is by modifying an existing example. For this reason, we will describe such an example here.

Launching the Workflow
----------------------



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

The workflow which runs the first-principles calculations can be different depending on which code you would like to run. Currently, only VASP is supported by default, with the :class:`.VaspFirstPrinciplesRun` workflow depicted below. It first runs an SCF calculation, and then uses the ``WAVECAR`` produced to run an NSCF bandstructure calculation and the Wannier input calculation.

|

.. image:: images/vasp_workflow_diagram.svg
    :width: 363px
    :align: center
    :alt: VASP workflow diagram

|
|

Customizing the workflow
------------------------

There are different ways in which you can customize the tight-binding extraction workflow to match your use case. If you already have the output from a first-principles calculation, you can directly use either the :class:`.WindowSearch`, :class:`.RunWindow` or :class:`.TightBindingCalculation` workflow, depending on which features you want to run. Also, you could change the workflow which is uded to run the first-principles calculations. When implementing such a workflow, you should make sure that it adheres to the interface defined in :class:`.FirstPrinciplesRunBase`, meaning that it should take *at least* the inputs defined there, and create the corresponding outputs. The easiest way to do this is by inheriting from the base class. The workflow can take *additional* inputs, which you can pass through the ``fp_run`` namespace in the :class:`OptimizeFirstPrinciplesTightBinding` workflow inputs. Finally, you can also use a different workflow for *evaluating* the tight-binding model. This allows you to create a measure for the quality of the model which fits best to your specific use case.
