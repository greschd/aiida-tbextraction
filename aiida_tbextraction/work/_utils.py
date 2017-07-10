#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

def create_workchain(typename, template, **kwargs):
    """
    Create a dynamic WorkChain type. Note that the module where this function is called must be available to the daemon. This means that dynamic WorkChains can be created in plugins, but not in the script that is used to start the WorkChain.

    :param typename: Class name of the resulting WorkChain.
    :type typename: str

    :param template: Template for the WorkChain. The class must be defined as ``class {typename}(WorkChain):`` in the template.
    :type template: str

    :param kwargs: Additional replacement parameters passed to the template via ``format``.
    """
    workchain_definition = template.format(typename=typename, **kwargs)
    namespace = dict(__name__='workchain_%s' % typename)
    exec(workchain_definition, namespace)
    result = namespace[typename]
    result._source = workchain_definition

    result.__module__ = sys._getframe(1).f_globals.get('__name__')
    return result
