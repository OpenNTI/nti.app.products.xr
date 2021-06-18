#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from io import BytesIO

import json

import random

import requests

from requests.exceptions import HTTPError

from pyramid import httpexceptions as hexc

from pyramid.view import view_config

from qrcode.image.svg import SvgImage

from qrcode.main import QRCode

from zope import component

from zope.cachedescriptors.property import Lazy

from zope.schema import ValidationError

from nti.app.base.abstract_views import AbstractView

from nti.dataserver.interfaces import IDataserverFolder

from nti.app.products.xr.interfaces import ICMI5LaunchParams
from nti.app.products.xr.interfaces import IDeviceHandoffStorage

from nti.externalization.externalization import to_external_object

logger = __import__('logging').getLogger(__name__)


_Z_BASE_32_ALPHABET = "13456789abcdefghijkmnopqrstuwxyz"

@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='templates/launch.pt',
             context=IDataserverFolder,
             name="launch_aspire")
class AuthenticatedUserView(AbstractView):
    """
    The launch url of our AU responsible for handing off a CMI5 launch
    to another device. There really isn't anything specific here to
    our backend system / product (nti.dataserver) or to our specific
    AUs. Frankly this is a faifly general process that could hand off
    any cmi5 launch to some process that can make xhr requests.

    The first step in the process, this view, takes the initial cmi5
    launch request, validates provided parameters, retrieves the
    LMS.LaunchData and stores it off temporarily in exchange for a
    code. The code is presented in basic UI as both a string and as a
    QR code.
    """

    @property
    def code(self):
        return self.token.code if self.token else None

    @Lazy
    def qr_svg(self):
        qr = QRCode(version=None)
        qr.add_data(self.code)
        qr.make(fit=True)
        image = qr.make_image(image_factory=SvgImage)

        stream = BytesIO()
        image.save(stream)
        stream.seek(0)
        return stream.read()

    def __call__(self):
        try:
            params = ICMI5LaunchParams(self.request)

            resp = requests.post(params.fetch)
            resp.raise_for_status()
            auth = resp.json()['auth-token']

            # TODO Our nti.xapi can do this request on our behalf
            # and deal with the nuts and bolts of this. We should move to that.
            headers = {
                'Authorization': 'Basic '+auth,
                'X-Experience-API-Version': '1.0.0'
            }
            state_params = dict(self.request.params)
            state_params['stateId'] = 'LMS.LaunchData'

            # The state api wants an agent param, not actor
            state_params['agent'] = state_params['actor']
            resp = requests.get(params.endpoint+'activities/state',
                                headers=headers,
                                params=state_params)
            try:
                resp.raise_for_status()
            except HTTPError as e:
                logger.exception('Bad request: %s', e.response.text)
                raise

            launch_data = resp.json()

            # We expect our launch params to be json. This bit I
            # suppose it not totally generally, the spec says this is
            # a string. Our AUs will use strings that represent json.
            launch_params = launch_data.get('launchParameters')
            if launch_params:
                try:
                    launch_data['launchParameters'] = json.loads(launch_params)
                except ValueError:
                    # We're the AU, so if we get something that can't
                    # be converted to json here that's a failure in
                    # our generation of the cmi5.xml declaration and
                    # it's unlikely that downstream can handle this.
                    # Fail fast? If this were to be more general we
                    # would probably rather opt to take the launch
                    # params as is in this case.
                    raise hexc.HTTPBadRequest()

            # Construct the payload we will ultimately provide to the
            # device that needs the launch data
            launch_info = {
                'launchData': launch_data,
                'endpoint': params.endpoint,
                'token': auth,
                'actor': to_external_object(params.actor),
                'registration': params.registration,
                'activityId': params.activityId
            }

            # TODO should we run this entire object through nti.externalization? That's
            # probably overkill here right now?
            data = json.dumps(launch_info)
            self.token = component.getUtility(IDeviceHandoffStorage).store_handoff_data(data)

            # If we roll our transaction back we will also roll our redis operation back.
            # Mark we had side effects so we don't do that implicitly.
            self.request.environ['nti.request_had_transaction_side_effects'] = True
        except ValidationError as e:
            logger.debug('Invalid launch request %s', e)
            raise hexc.HTTPBadRequest()

        return {'mode': 'launch',
                'target': 'aspire',
                'code': self.code,
                'launch_params': params,
                'launch_data': resp.text,
                'auth': auth}


@view_config(route_name='objects.generic.traversal',
             request_method='GET',
             renderer='rest',
             context=IDataserverFolder,
             name="launch_aspire_handoff")
class LaunchHandoffView(AbstractView):
    """
    The second part of the handoff exchanges a code provided by query
    param for the launch data. IDeviceHandoffStorage enforces the
    codes are one time use and short lived. Should we consider also
    rate limiting this API?
    """

    def __call__(self):
        storage = component.getUtility(IDeviceHandoffStorage)
        code = self.request.params.get('code')
        if not code:
            raise hexc.HTTPBadRequest()
        
        try:
            data = storage.get_handoff_data(code)
        except KeyError:
            raise hexc.HTTPNotFound()

        # Mark sideeffects so we don't put the data back in redis when
        # the GET request rolls back the transaction.
        self.request.environ['nti.request_had_transaction_side_effects'] = True

        # Our data is a json encoded string. We could round trip it
        # back through the json module or nti.externalization, but
        # that seems wasted. If redis isn't a trusted source seems
        # like we had bigger issues.
        response = self.request.response
        response.status_code = 200
        response.content_type = 'application/json'
        response.body = data
        return response
