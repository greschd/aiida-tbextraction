Installation and Setup
======================

Before using ``aiida-tbextraction``, you will need to install it and set up the required codes in AiiDA. This section will guide you through this process.

Installation
------------

First, you need to install AiiDA. If you haven't done so already, please follow the instructions in the `AiiDA documentation <http://aiida-core.readthedocs.io/en/latest/installation>`_. Note that you need at least version 1.0 of AiiDA to run ``aiida-tbextraction``.

Once AiiDA is set up, you can install the plugin with

.. code:: bash

    python -m pip install aiida-tbextraction

where ``python`` should be the interpreter for which you installed AiiDA.

Setup
-----

Next, we need to install and set up the codes that ``aiida-tbextraction`` uses. Specifically, you will need

* `TBmodels <http://z2pack.ethz.ch/tbmodels>`_
* `bands-inspect <http://bands-inspect.readthedocs.io>`_
* `symmetry-representation <http://z2pack.ethz.ch/symmetry-representation>`_ (only if you want to symmetrize the model)
* `Wannier90 <http://wannier.org>`_
* VASP, or another DFT code (currently only VASP is natively supported)

The packages ``tbmodels``, ``bands-inspect`` and ``symmetry-representation`` are Python 3 codes. As such, you can install them with

.. code:: bash

    python3 -m pip install tbmodels bands-inspect symmetry-representation

This will install the command-line tools ``tbmodels``, ``bands-inspect`` and ``symmetry-repr``. To add these codes to AiiDA, you can use the ``verdi code setup`` command. The absolute path to the command-line tools can be found with ``which``, for example

.. code:: bash

    which tbmodels

Make sure to add ``unset PYTHONPATH`` as a "prepend text" for the code. Otherwise, the ``PYTHONPATH`` used by AiiDA will interfere with these tools. Since the calls to these codes are relatively quick, it usually makes sense to install them on your local computer instead of a separate compute cluster.

For Wannier90 and the DFT code, you should follow the regular install instructions for compiling the code, and then set them up in AiiDA with ``verdi code setup``.

Once you have these codes set up, you're ready to create some tight-binding models!
