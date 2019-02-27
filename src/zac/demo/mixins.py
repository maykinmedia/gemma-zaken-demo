from requests import HTTPError
from zds_client import ClientError
from zds_client.log import Log

from .utils import render_exception_to_response


class ZACViewMixin:
    """
    Wraps the entire dispatch method to catch `ClientError`s. If caught, it
    renders a nice error page. If you want to do stuff in the `dispatch`
    method, use the `_pre_dispatch` or `_post_dispatch` methods.
    """
    keep_logs = False

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
        clear_logs = not self.keep_logs and not request.GET.get('keep-logs', False)
        if clear_logs:
            Log.clear()

        try:
            self._pre_dispatch(request, *args, **kwargs)

            result = super().dispatch(request, *args, **kwargs)

            self._post_dispatch(request, *args, **kwargs)
        except (ClientError, HTTPError) as e:
            return render_exception_to_response(request, e)

        return result

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
