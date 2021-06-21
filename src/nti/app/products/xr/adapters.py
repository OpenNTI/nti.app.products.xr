from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import json

from zope import interface

from zope.schema import getFields
from zope.schema import getValidationErrors

from zope.schema.interfaces import IFromUnicode

from nti.externalization import update_from_external_object

from nti.schema.fieldproperty import createDirectFieldProperties

from nti.schema.schema import SchemaConfigured

from nti.xapi.entities import Agent

from nti.app.products.xr.interfaces import ICMI5LaunchParams

@interface.implementer(ICMI5LaunchParams)
class CMI5LaunchParams(SchemaConfigured):

    createDirectFieldProperties(ICMI5LaunchParams)


def launch_params_from_request(request):
    """
    Turn a pyramid request into an ICMI5LaunchParams and validate that
    the incoming parameters meet the CMI spec.
    """

    params = CMI5LaunchParams()

    for name, field in getFields(ICMI5LaunchParams).items():
        val = request.params.get(name)
        if val:
            if field is ICMI5LaunchParams['actor']:
                json_val = val
                val = Agent()
                update_from_external_object(val, json.loads(json_val))
            elif IFromUnicode.providedBy(field):
                val = field.fromUnicode(val)
        setattr(params, name, val)

    # validate
    errors = getValidationErrors(ICMI5LaunchParams, params)
    if errors:
        __traceback_info__ = errors
        raise errors[0][1]

    return params
