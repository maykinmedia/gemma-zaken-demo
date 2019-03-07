import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer


class UserNotificationConsumer(WebsocketConsumer):
    def connect(self):
        username = self.scope['url_route']['kwargs']['username']

        # Topic
        self.group_name = 'notifications_%s' % username

        # Join group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave group
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        raise NotImplemented()

    # Send a message to the WebSocket
    def notification_message(self, event):
        message = event['message']

        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
