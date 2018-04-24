AiiDA tight-binding extraction
==============================

``aiida-tbextraction`` is an `AiiDA <http://aiida.net>`_ plugin for creating first-principles based Wannier tight-binding models. It defines workflows that can be used to automatically run a first-principles calculation, extract a tight-binding model using `Wannier90 <http://wannier.org>`_, and perform post-processing steps such as symmetrization with `TBmodels <http://z2pack.ethz.ch/tbmodels>`_. Additionally, the energy windows used in Wannier90 can be automatically optimized, for example to achieve a better band-structure fit.

Please cite:

* *High-throughput construction of symmetrized Wannier tight-binding models from ab initio calculations*, D. Gresch, Q.S. Wu, G. Winkler, R. Häuselmann, M. Troyer, and A. A. Soluyanov,  *in preparation*.
* *AiiDA: automated interactive infrastructure and database for computational science*, G. Pizzi, A. Cepellotti, R. Sabatini, N. Marzari, and B. Kozinsky, `Comp. Mat. Sci. 111, 218-230 (2016) <http://dx.doi.org/10.1016/j.commatsci.2015.09.013>`_
* *An updated version of wannier90: A tool for obtaining maximally-localised Wannier functions*, A. A. Mostofi, J. R. Yates, G. Pizzi, Y. S. Lee, I. Souza, D. Vanderbilt, N. Marzari `Comput. Phys. Commun. 185, 2309 (2014) <http://dx.doi.org/10.1016/j.cpc.2014.05.003>`_

.. toctree::
   :maxdepth: 2

   tutorial/index.rst
   reference/index.rst
   package_structure.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
