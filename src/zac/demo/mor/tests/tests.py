import collections
import json
import requests
from django_webtest import WebTest
from time import sleep

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext

from ...models import SiteConfiguration

from .factories import *


api_scope = 'api/v1/'


def get_user_json(user):

    return json.dumps({
        'username': user.username,
        'password': user.password
    })


class TestViews(WebTest):

    json_header = {
        'Content-Type': 'application/json'
    }

    def get_test_zaak(self):
        return json.dumps({
            "bronorganisatie": "509381406",
            "registratiedatum": "2018-12-06",
            "startdatum": "2018-12-06",
            "toelichting": "Hier ben ik",
            "verantwoordelijkeOrganisatie": "245122461",
            "zaakgeometrie": {"coordinates": [4.891362190246582, 52.3731887966551],
                              "type": "Point"},
            "zaaktype": "{{zaaktype}}"
        })

    def setUp(self):
        self.test_url = settings.TEST_PLATFORM_URL
        self.config = SiteConfigurationFactory()
        self.user = UserFactory()

        # getting the key for the authentication
        self.key = requests.post(
            '{}/api/auth/login/'.format(self.test_url),
            data=get_user_json(self.user),
            headers=self.json_header)\
            .json()['key']

        self.json_header['Authorization'] = 'Token {}'.format(self.key)

        # create a new session
        create_session = requests.post(
            '{}/api/v1/testsessions/'.format(self.test_url),
            data=json.dumps({
                'session_type': 2 # FIXME: MOR sessie, use a natural_key?
            }),
            headers=self.json_header
        ).json()
        self.session_id = create_session['id']
        print("Started session id " + str(self.session_id))
        # save the urls just created
        for i in create_session['exposedurl_set']:
            if i['vng_endpoint'] == 'ZRC':
                self.config.zrc_base_url = i['exposed_url']+api_scope
            elif i['vng_endpoint'] == 'ZTC':
                self.config.ztc_base_url = i['exposed_url']+api_scope
            else:
                pass
                # TODO: for the other cases
        self.config.orc_base_url = ''
        self.config.brc_base_url = ''
        self.config.drc_base_url = ''
        self.config.save()
        self.config.reload_config()

    def test_create_view(self):
        call = self.app.get(reverse('demo:mor-index'))
        form = call.forms[0]
        form['toelichting'] = 'Test text'
        resp = form.submit(status=[302])
#        requests.get(
#            '{}/api/v1/stop-session/{}'.format(self.test_url, self.session_id),
#            headers=self.json_header
#        )
        res = requests.get(
            '{}/api/v1/result-session/{}'.format(self.test_url, self.session_id),
            headers=self.json_header
        )
        res = res.json()['result']
        self.assertEqual(res, 'success')

    def test_create_view_no_field(self):
        call = self.app.get(reverse('demo:mor-index'))
        form = call.forms[0]
        resp = form.submit()
        self.assertContains(resp, 'This field is required')
