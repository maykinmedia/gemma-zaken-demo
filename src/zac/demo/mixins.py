from requests import HTTPError
from zds_client import ClientError
from zds_client.log import Log

from .utils import render_exception_to_response


class ExceptionViewMixin:
    """
    Wraps the entire dispatch method to catch `ClientError`s. If caught, it
    renders a nice error page. If you want to do stuff in the `dispatch`
    method, use the `_pre_dispatch` or `_post_dispatch` methods.
    """
    def _pre_dispatch(self, request, *args, **kwargs):
        """
        Any code you want to call before calling the main dispatch method.
        """
        pass

    def _post_dispatch(self, request, *args, **kwargs):
        """
        Any code you want to call after calling the main dispatch method.
        """
        pass

    def dispatch(self, request, *args, **kwargs):
        try:
            self._pre_dispatch(request, *args, **kwargs)

            result = super().dispatch(request, *args, **kwargs)

            self._post_dispatch(request, *args, **kwargs)
        except (ClientError, HTTPError) as e:
            return render_exception_to_response(request, e)

        return result


class LogViewMixin:
    keep_logs = False

    def get(self, request, *args, **kwargs):
        """
        Only clear the log AFTER a GET-request. This way, POST-requests are
        included in the network logs.

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        if not self.keep_logs and not request.GET.get('keep-logs', False):
            Log.clear()

        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """
        Clear the logs before a POST-request.

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        Log.clear()

        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Include log entries in the response.

        :param kwargs:
        :return:
        """
        context = super().get_context_data(**kwargs)

        context.update({
            'log_entries': Log.entries(),
        })

        return context


class ZACViewMixin(LogViewMixin, ExceptionViewMixin):
    pass
