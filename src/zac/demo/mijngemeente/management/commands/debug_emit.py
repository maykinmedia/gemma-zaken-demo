import datetime
import json

from django.core.management.base import BaseCommand, CommandError

import pika

from zac.demo.models import SiteConfiguration


class Command(BaseCommand):
    """
    Example:

        $ ./manage.py debug_emit --kenmerk=foo.bar.test "test message"
    """
    help = 'Sends a notification to an AMQP server.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--kenmerk',
            action='store',
            dest='routing_key',
            default='foo.bar',
            help='Filters om het op een bepaalde queue te plaatsen.',
        )
        parser.add_argument(
            '--kanaal',
            action='store',
            dest='exchange',
            default='zaken',
            help='Kanaal of exchange om mee te verbinden.',
        )
        parser.add_argument(
            'message',
            nargs=1,
            type=str,
            help='Het bericht dat moet worden verstuurd.'
        )

    def handle(self, *args, **options):
        nc_routing_key = options.get('routing_key')

        # Grab configuration
        config = SiteConfiguration.get_solo()
        nc_host = 'localhost'  # config.nc_host
        nc_port = 5672  # config.nc_port
        nc_exchange = options.get('exchange')

        message = options.get('message')[0]

        # Set up connection and channel
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=nc_host, port=nc_port))
        channel = connection.channel()

        # Make sure we attach to the correct exchange.
        channel.exchange_declare(
            exchange=nc_exchange,
            exchange_type='topic'
        )

        channel.basic_publish(exchange=nc_exchange,
                              routing_key=nc_routing_key,
                              body=message)

        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%I')
        self.stdout.write(f'[{now}] Verstuurd met kenmerk "{nc_routing_key}": {message}')

        connection.close()
