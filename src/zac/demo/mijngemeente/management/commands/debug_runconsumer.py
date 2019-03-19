import datetime

from django.core.management.base import BaseCommand

import pika

from zac.demo.models import SiteConfiguration


class Command(BaseCommand):
    """
    Example:

        $ ./manage.py runconsumer foo.bar.*'
    """
    help = 'Start consumer that connects to an AMQP server to listen for notifications.'

    def add_arguments(self, parser):
        parser.add_argument(
            'filters',
            nargs='*',
            type=str,
            help='Een of meer filters waar berichten voor ontvangen moeten worden.'
        )

    def handle(self, *args, **options):
        # Reading guide:
        #
        # * A producer is a user application that sends messages (ie. ZRC).
        # * An exchange is where messages are sent to (ie. zaken).
        # * A queue is a buffer that stores (relevant) messages (ie. zaken with
        #   zaaktype X).
        # * A consumer is a user application that receives messages (ie. this
        #   demo: Mijn Gemeente).

        filters = options.get('filters')
        if len(filters) == 0:
            binding_keys = '#'  # All messages
        else:
            binding_keys = filters

        # Grab configuration
        config = SiteConfiguration.get_solo()
        nc_host = 'localhost'  # config.nc_host
        nc_port = 5672  # config.nc_port
        nc_exchange = 'zaken'  # config.nc_exchange

        # Set up connection and channel
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=nc_host, port=nc_port))
        channel = connection.channel()

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
        self.stdout.write(
            f'Starting consumer connected to amqp://{nc_host}:{nc_port}\n'
            f'Listening on exchange "{nc_exchange}" with topic: {filters}\n'
            f'Quit with CTRL-BREAK.'
        )

        def callback(ch, method, properties, body):
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%I')
            self.stdout.write(f'[{now}] Ontvangen met kenmerk "{method.routing_key}": {body}')

        channel.basic_consume(
            callback,
            queue=queue_name,
            no_ack=True
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            return
