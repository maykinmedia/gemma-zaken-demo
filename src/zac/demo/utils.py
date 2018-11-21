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
            error.invalid_params = error.get('invalid-params', None)
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
