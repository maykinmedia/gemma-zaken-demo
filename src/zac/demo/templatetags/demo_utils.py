import re
import urllib.parse

from django import template
from django.template.defaultfilters import stringfilter

uuid_pattern = re.compile(r'([a-f0-9]{3})[a-f0-9]{5}-[a-f0-9]{4}-4[a-f0-9]{3}-[89aAbB][a-f0-9]{3}-[a-f0-9]{9}([a-f0-9]{3})')

register = template.Library()


@register.filter
@stringfilter
def shorten_api_url(url):
    """
    Shortens an API URL by replacing all UUIDs with the first and last 3
    characters.

    :param url: The URL.
    :return: The shortened URL.
    """
    return re.subn(uuid_pattern, '\\1..\\2', url)[0]


@register.filter
def pretty_urlencode(query_params):
    """
    Shortens an API URL by replacing all UUIDs with the first and last 3
    characters.

    :param url: The URL.
    :return: The shortened URL.
    """
    if not query_params:
        return ''
    return '&'.join(f'{k}={v}' for k, v in query_params.items())
