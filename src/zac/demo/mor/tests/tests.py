import collections
import json
import os
import urllib3

import requests
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext
from django.conf import settings

from zac.accounts.models import User

from django_webtest import WebTest
from ...models import SiteConfiguration

API_SCOPE = 'api/v1/'
SUCCESS_RESULT = 'success'

user = User(username='test', password='test1234')

offline = False


def check_connectivity():
    try:
        global offline
        http = urllib3.PoolManager()
        response = http.request('GET', 'https://www.google.com/')
        offline = False
        param = os.environ.get('offline')
        if param is not None:
            offline = param.lower() == 'true'
    except Exception as e:
        offline = True


def get_user_json(user):

    return json.dumps({
        'username': user.username,
        'password': user.password
    })


class TestViews(WebTest):

    json_header = {
        'Content-Type': 'application/json'
    }

    get_test_zaak = {
        "bronorganisatie": "509381406",
        "registratiedatum": "2018-12-06",
        "startdatum": "2018-12-06",
        "toelichting": "Hier ben ik",
        "verantwoordelijkeOrganisatie": "245122461",
        "zaakgeometrie": {"coordinates": [4.891362190246582, 52.3731887966551],
                          "type": "Point"},
        "zaaktype": "{{zaaktype}}"
    }

    def setUp(self):
        check_connectivity()
        if offline:
            return
        self.session_type = 'MOR sessie'
        self.session_type_pk = 2
        self.test_text = 'Test text'
        self.test_url = settings.TEST_PLATFORM_URL
        self.config = SiteConfiguration(
            ztc_catalogus_uuid='f7afd156-c8f5-4666-b8b5-28a4a9b5dfc7',
            global_api_client_id='demo-app-KK2CG69NTrSN',
            global_api_secret='wo1hW8oHsM0U9hSTnMM0jtCbD8GYmf4i',
            ztc_mor_zaaktype_uuid='0119dd4e-7be9-477e-bccf-75023b1453c1',
            ztc_mor_informatieobjecttype_image_uuid='63a58060-8cd1-4c9d-bcc4-b6954353e758',
        )
        self.config.save()
        self.user = user
        # self.addCleanup(self.cache.clear)

        # getting the key for the authentication
        self.key = (requests.post(
            '{}/api/auth/login/'.format(self.test_url),
            data=get_user_json(self.user),
            headers=self.json_header))
        self.key = self.key.json()['key']

        self.json_header['Authorization'] = 'Token {}'.format(self.key)

        # create a new session
        create_session = requests.post(
            '{}/api/v1/testsessions/'.format(self.test_url),
            data=json.dumps({
                'session_type': self.session_type
            }),
            headers=self.json_header
        ).json()
        self.session_id = create_session['id']
        # save the urls just created
        for i in create_session['exposedurl_set']:
            if i['vng_endpoint'] == 'ZRC':
                self.config.zrc_base_url = f'{i["exposed_url"]}{API_SCOPE}'
            elif i['vng_endpoint'] == 'ZTC':
                self.config.ztc_base_url = f'{i["exposed_url"]}{API_SCOPE}'

        self.config.orc_base_url = ''
        self.config.brc_base_url = ''
        self.config.drc_base_url = ''
        self.config.save()
        self.config.reload_config()

    def test_create_view(self):
        if offline:
            return
        index = self.app.get(reverse('demo:mor-index'))
        form = index.forms[0]
        form['toelichting'] = self.test_text
        resp = form.submit(status=[302, 200])
        requests.get(
            '{}/api/v1/stop-session/{}'.format(self.test_url, self.session_id),
            headers=self.json_header
        )
        res = requests.get(
            '{}/api/v1/result-session/{}'.format(self.test_url, self.session_id),
            headers=self.json_header
        )
        res = res.json()['result']
        self.assertEqual(res, SUCCESS_RESULT)

    def test_create_view_no_field(self):
        if offline:
            return
        call = self.app.get(reverse('demo:mor-index'))
        form = call.forms[0]
        resp = form.submit()
        self.assertTrue('Dit veld is verplicht.' in str(resp.html))
