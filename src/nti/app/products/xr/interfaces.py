from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from zope import interface

from nti.schema.field import Mapping
from nti.schema.field import HTTPURL
from nti.schema.field import Object
from nti.schema.field import ValidTextLine
from nti.schema.field import ValidURI

from nti.xapi.interfaces import IAgent
from nti.xapi.interfaces import _check_uuid

class IAndroidLaunchTarget(interface.Interface):
    """
    Represents a launch target (bundle) and intent extras
    for a particular android based application.
    """

    bundleId = ValidTextLine(title=u'The id of the android bundle to launch',
                             required=True)

    extras = Mapping(title=u'Android intent extras to launch with',
                     key_type=ValidTextLine(),
                     value_type=Object(interface.Interface),
                     required=True,
                     default={})

class ICMI5LaunchRequest(interface.Interface):
    """
    A marker interface for requests that are CMI5 Launch Requests
    """
ICMI5LaunchRequest.setTaggedValue('_ext_is_marker_interface', True)


class ICMI5LaunchParams(interface.Interface):
    """
    Encapsulates the CMI5 launch request parameters.

    See: https://github.com/AICC/CMI-5_Spec_Current/blob/quartz/cmi5_spec.md#81-launch-method
    """

    endpoint = HTTPURL(title=u'A URL to the LMS listener location for xAPI requests to be sent to.',
                       required=True)

    fetch = HTTPURL(title=u'The fetch URL is used by the AU to obtain an authorization token created and managed by the LMS. The authorization token is used by the AU being launched.',
                    required=True)

    actor = Object(IAgent,
                   title=u'Identifies the learner launching the AU so the AU will be able to include it in xAPI requests.',
                   required=True)

    registration = ValidTextLine(title=u'A Registration ID corresponding to the learner\'s enrollment for the AU being launched.',
                                 required=False,
                                 constraint=_check_uuid)

    activityId = ValidURI(title=u'The Activity ID of the AU being launched.',
                        required=True)


class IHandoffToken(interface.Interface):

    code = ValidTextLine(title=u'A unique code identifying this token',
                         required=True)

class IHandoffTokenGenerator(interface.Interface):

    def generate_token(self):
        """
        Generate a unique IHandoffToken
        """

class IDeviceHandoffStorage(interface.Interface):
    """
    An object that can temporarily store handoff data in exchange for
    a token. It is expected that implmentations will store this data
    only for a short life time.
    """

    def store_handoff_data(data):
        """
        Stores the provided handoff data and returns an IHandoffToken whose
        code can be used to retrieve the data at some point in the future.
        """

    def get_handoff_data(code):
        """
        Retrieve the handoff data previously stored for the provided
        code. If data for the code no longer exists a KeyError will be raised.
        """
