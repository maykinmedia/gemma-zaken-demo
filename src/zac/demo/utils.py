from datetime import datetime
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from zds_client import ClientError
from zds_client.log import Log


def exception_to_validation_errors(exc):
    """
    Converts a `ClientError` that is of code "invalid" to a list of
    `ValidationError`s.

    :param exc: The `ClientError`.
    :return: A `list` of `ValidationError`s or None if the `Exception` did not
             hold any invalid params.
    """

    if type(exc) is ClientError and len(exc.args) >= 1 and type(exc.args[0]) is dict:

        error = exc.args[0]
        if error['code'] == 'invalid' and 'invalid-params' in error:
            return [
                ValidationError('{}: {}'.format(param['name'], param['reason']), code=param['code'])
                for param in error['invalid-params']
            ]

    return None


def render_exception_to_response(request, exc, context=None):
    """
    Shortcut function to render a template with the exception nicely formatted.

    :param request: The request passed to the view.
    :param exc: The `Exception` or `ClientError`.
    :param context: Additional context as a `dict` to pass to the template.
    :return: A stringified response.
    """
    if context is None:
        context = {}

    error = None
    if type(exc) is ClientError:
        try:
            error = exc.args[0]
            error['invalid_params'] = error.get('invalid-params', None)
        except Exception:
            pass

    context.update({
        'view': {
            'title': _('Foutmelding'),
            'subtitle': _('Er ging iets mis...'),
        },
        'error': error,
        'exception': exc,
        'log_entries': Log.entries()
    })

    return render(request, 'demo/error.html', context)


def api_response_list_to_dict(lst, key=None):
    """
    Convert an API response containing a `list` of objects, to a `dict` where
    the key is an element from the object. By default they `key` = `url`.

    :param lst: The `list` from JSON response.
    :param key: The key to use in the resulting `dict`.
    :return: A `dict` with all objects from `lst` addressable by the `key`.
    """
    # TODO: The by-url pattern might be so common it should be in the client.

    if key is None:
        key = 'url'

    return {
        el[key]: el for el in lst
    }


def isodate(dt=None):
    """
    Returns a ISO-compliant date.

    :param dt: Any `datetime`. Defaults to `datetime.now()`.
    :return: A `string` with the date.
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%Y-%m-%d')


def extract_page_from_url(url: str, page_param='page') -> int:
    querystring = urlparse(url).query
    return int(parse_qs(querystring)[page_param][0])


def extract_pagination_info(response: dict, page_param='page') -> dict:
    url_next = response.get('next')
    url_previous = response.get('previous')

    pagination = {
        'count': response['count'],
        'next': url_next,
        'previous': url_previous,
        'page_nr': 1,
    }

    if url_next:
        pagination['page_nr'] = extract_page_from_url(url_next) - 1
    elif url_previous:
        pagination['page_nr'] = extract_page_from_url(url_previous) + 1

    return pagination


def get_uuid(url, index=-1):
    return url.split('/')[index]


def format_dict_diff(changes):
    res = []
    for change in changes:
        if change[0] == 'add' or change[0] == 'remove':
            if not change[1]:
                res.append((change[0], dict(change[2])))
        elif change[0] == 'change':
            res.append((change[0], {change[1]: change[2]}))
    return res
