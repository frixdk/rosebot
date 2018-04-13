from django.core.management.base import BaseCommand

from events.utils import handle_event_message


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("This is just for testing", args, options)

        msg = {
            "type": "message",
            "channel": "GA66YSWAX",  # put private channel here
            "user": "UA11Y58SJ",  # your user id here
            "text": "fredag",
            "ts": "1355517523.000005"
        }

        handle_event_message(msg)
