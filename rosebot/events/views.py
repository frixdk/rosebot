import datetime
import random
import re
import xml.etree.ElementTree as ET

import requests
from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from slugify import slugify

from events.utils import handle_event_message
from slackclient import SlackClient


class Events(APIView):
    def post(self, request, *args, **kwargs):
        slack_message = request.data

        if slack_message.get('token') != settings.SLACK_VERIFICATION_TOKEN:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # verification challenge
        if slack_message.get('type') == 'url_verification':
            return Response(data=slack_message,
                            status=status.HTTP_200_OK)

        if 'event' in slack_message:
            event_message = slack_message.get('event')

            # ignore bot's own message
            if event_message.get('subtype') == 'bot_message':
                return Response(status=status.HTTP_200_OK)

            handle_event_message(event_message)

        return Response(status=status.HTTP_200_OK)


class Vejr(APIView):
    def get(self, request, *args, **kwargs):
        r = requests.get('https://www.yr.no/sted/Danmark/Nordjylland/%C3%85lborg/forecast.xml')
        root = ET.fromstring(r.content)
        forecast = root.find('forecast').find('tabular').find('time')
        temp = forecast.find('temperature')
        symbol = forecast.find('symbol')

        return Response(status=status.HTTP_200_OK)
