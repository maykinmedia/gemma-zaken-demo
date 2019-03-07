from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

import zac.demo.mijngemeente.routing

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            zac.demo.mijngemeente.routing.websocket_urlpatterns
        )
    ),
})
