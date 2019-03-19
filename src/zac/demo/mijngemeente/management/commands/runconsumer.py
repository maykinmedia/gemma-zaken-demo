import datetime

from django.core.management.base import BaseCommand, CommandError

import pika

from zac.demo.models import NotifyMethod, SiteConfiguration


class Command(BaseCommand):
    """
    Example:

        $ ./manage.py runconsumer'
    """
    help = 'Start consumer that connects to an AMQP server to listen for notifications.'

    def handle(self, *args, **options):
        # Reading guide:
        #
        # * A producer is a user application that sends messages (ie. ZRC).
        # * An exchange is where messages are sent to (ie. zaken).
        # * A queue is a buffer that stores (relevant) messages (ie. zaken with
        #   zaaktype X).
        # * A consumer is a user application that receives messages (ie. this
        #   demo: Mijn Gemeente).

        # Grab configuration
        config = SiteConfiguration.get_solo()

        nc_host = config.nc_amqp_host
        nc_port = int(config.nc_amqp_port) if config.nc_amqp_port else pika.ConnectionParameters._DEFAULT

        exchanges_binding_keys = config.get_nc_channels_and_filters()

        if len(exchanges_binding_keys) == 0:
            raise CommandError('No exchange(s) configured.')

        # Set up connection and channel
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=nc_host, port=nc_port))
        channel = connection.channel()

        # Start listening...
        self.stdout.write(f'Starting consumer connected to amqp://{nc_host}:{connection._impl.params.port}')

        for nc_exchange, binding_keys in exchanges_binding_keys:
            # Make sure we attach to the correct exchange.
            channel.exchange_declare(
                exchange=nc_exchange,
                exchange_type='topic'
            )

            # Create a (randomly named) queue just for me
            result = channel.queue_declare(exclusive=True)
            queue_name = result.method.queue

            for binding_key in binding_keys:
                channel.queue_bind(
                    exchange=nc_exchange,
                    queue=queue_name,
                    routing_key=binding_key
                )

            filters = ', '.join(binding_keys)
            self.stdout.write(f'Listening on exchange "{nc_exchange}" with topic: {filters}')

            # Define callback to be triggered when a notification is received.
            def callback(ch, method, properties, body):
                now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%I')
                self.stdout.write(f'[{now}] Ontvangen op "{nc_exchange}" met kenmerk "{method.routing_key}": {body}')

            channel.basic_consume(
                callback,
                queue=queue_name,
                no_ack=True
            )

        self.stdout.write(f'Quit with CTRL-BREAK.')

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            return
