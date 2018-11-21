from requests import HTTPError
from zds_client import ClientError

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

