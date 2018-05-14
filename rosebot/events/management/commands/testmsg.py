from django.core.management.base import BaseCommand

from events.utils import handle_event_message


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('msg', type=str)

    def handle(self, *args, **options):
        print("This is just for testing", args, options)
        msg = options.pop('msg', '')

        msg = {
            "type": "message",
            "channel": "GA66YSWAX",  # put private channel here
            "user": "UA11Y58SJ",  # your user id here
            "text": msg,
            "ts": "1525252116.000231"
        }

        handle_event_message(msg)
