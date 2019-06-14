from rest_framework.permissions import AllowAny
from vng_api_common.notifications.api.views import NotificationView


class CallbackView(NotificationView):
    action = 'create'
    # The application in reality *should* make some checks but not via the AC.
    authentication_classes = ()
    permission_classes = (AllowAny, )
