import datetime
import os
import shutil
import subprocess
import tempfile
from urllib.parse import urljoin

import requests
import yaml

from .schema import get_operation_url
from .conf import settings


class Swagger2OpenApi:
    """
    Wrapper around node swagger2openapi
    """

    def __init__(self, swagger: bytes):
        self.swagger = swagger

    def convert(self) -> dict:
        tempdir = tempfile.mkdtemp()

        infile = os.path.join(tempdir, 'swagger2.0.yaml')
        outfile = os.path.join(tempdir, 'openapi.yaml')

        try:
            with open(infile, 'wb') as _infile:
                _infile.write(self.swagger)

            cmd = '{bin} {infile} --outfile {outfile}'.format(
                bin=os.path.join(*'node_modules/.bin/swagger2openapi'.split('/')),
                infile=infile,
                outfile=outfile,
            )
            subprocess.call(cmd, shell=True, cwd=settings.base_dir)

            with open(outfile, 'rb') as _outfile:
                return yaml.safe_load(_outfile)

        finally:
            shutil.rmtree(tempdir)


class Log:
    _entries = []
    max_entries = 100

    @classmethod
    def add(cls, service, url, method, request_headers, request_data, response_status, response_headers, response_data):
        # Definitly not thread-safe
        if len(cls._entries) >= cls.max_entries:
            cls._entries.pop(0)

        entry = {
            'timestamp': datetime.datetime.now(),
            'service': service,
            'request': {
                'url': url,
                'method': method,
                'headers': request_headers,
                'data': request_data,
            },
            'response': {
                'status': response_status,
                'headers': response_headers,
                'data': response_data,
            }
        }

        cls._entries.append(entry)

    @classmethod
    def clear(cls):
        cls._entries = []

    @classmethod
    def entries(cls):
        return cls._entries


class Client:
    _schema = None
    _log = Log()

    def __init__(self, service: str, base_path: str='/api/v1/'):
        self.service = service
        self.base_path = base_path

    @property
    def log(self):
        """
        Local log entries.
        """
        return (entry for entry in self._log.entries() if entry['service'] == self.service)

    @property
    def base_url(self) -> str:
        config = settings.config[self.service]
        return "{scheme}://{host}:{port}{path}".format(
            scheme=config['scheme'],
            host=config['host'],
            port=config['port'],
            path=self.base_path,
        )

    @property
    def schema(self):
        if self._schema is None:
            self.fetch_schema()
        return self._schema

    def request(self, path, method='GET', **kwargs):
        url = urljoin(self.base_url, path)
        headers = kwargs.pop('headers', {})
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Accept-Crs', 'EPSG:4326')
        headers.setdefault('Content-Type', 'application/json')
        kwargs['headers'] = headers

        response = requests.request(method, url, **kwargs)
        try:
            response_json = response.json()
        except:
            response_json = None

        self._log.add(
            self.service,
            url,
            method,
            headers,
            kwargs.get('data', kwargs.get('json', None)),
            response.status_code if response else None,
            dict(response.headers) if response else None,
            response_json,
        )

        return response

    def fetch_schema(self):
        url = urljoin(self.base_url, 'schema/openapi.yaml')
        response = requests.get(url)
        swagger2openapi = Swagger2OpenApi(response.content)
        self._schema = swagger2openapi.convert()

    def retrieve(self, resource: str, **path_kwargs):
        operation_id = '{resource}_read'.format(resource=resource)
        url = get_operation_url(self.schema, operation_id, **path_kwargs)
        response = self.request(url)
        assert response.status_code == 200, response.json()
        return response.json()

    def list(self, resource: str, **path_kwargs):
        operation_id = '{resource}_list'.format(resource=resource)
        url = get_operation_url(self.schema, operation_id, **path_kwargs)
        response = self.request(url)
        assert response.status_code == 200, response.json()
        return response.json()

    def create(self, resource: str, data: dict, **path_kwargs):
        operation_id = '{resource}_create'.format(resource=resource)
        url = get_operation_url(self.schema, operation_id, **path_kwargs)
        response = self.request(url, method='POST', json=data)
        assert response.status_code == 201, response.json()
        return response.json()
