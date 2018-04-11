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

from slackclient import SlackClient

SLACK_VERIFICATION_TOKEN = getattr(settings, 'SLACK_VERIFICATION_TOKEN', None)
SLACK_BOT_USER_TOKEN = getattr(settings,'SLACK_BOT_USER_TOKEN', None)
Client = SlackClient(SLACK_BOT_USER_TOKEN)

class Events(APIView):
    def post(self, request, *args, **kwargs):
        def replace_keep_case(word, replacement, text):
            def func(match):
                g = match.group()
                if g.islower(): return replacement.lower()
                if g.istitle(): return replacement.title()
                if g.isupper(): return replacement.upper()
                return replacement
            return re.sub(word, func, text, flags=re.I)

        def get_rose_message():
            rose_messages = [
                'Det er pissefint rosévejr',
                'Det bliver ikke bedre',
                "Åh gu' så fint et rosévejr",
                'Rosévejr? Bare hæld op',
                "Åh som du vil ha'",
            ]
            secure_random = random.SystemRandom()
            return secure_random.choice(rose_messages)

        def get_user_display(user):
            response = Client.api_call(
                "users.info",
                user=user
            )

            if response.get('ok'):
                return response.get('user').get('profile').get('display_name')

            return ''

        slack_message = request.data

        print("data:", slack_message)

        if slack_message.get('token') != SLACK_VERIFICATION_TOKEN:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # verification challenge
        if slack_message.get('type') == 'url_verification':
            return Response(data=slack_message,
                            status=status.HTTP_200_OK)
        # greet bot
        if 'event' in slack_message:
            event_message = slack_message.get('event')

            # ignore bot's own message
            if event_message.get('subtype') == 'bot_message':
                return Response(status=status.HTTP_200_OK)

            # process user's message
            user = event_message.get('user')
            text = event_message.get('text')
            channel = event_message.get('channel')
            timestamp = event_message.get('ts')

            im = text.lower()
            sim = slugify(text.lower())

            bot_text = ''
            if 'polen' in sim:
                now = datetime.datetime.now()
                polen = datetime.date(2018, 5, 10)
                now = datetime.datetime.now()
                polen = datetime.datetime(2018, 5, 10, 10, 0, 0)
                delta = polen - now
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds // 60) % 60
                bot_text = 'Der er {} dage, {} timer og {} minutter til Polen'.format(days, hours, minutes)
            elif 'stax' in im:
                bot_text = "'Stax players are agents of Satan' - Hitler 1997 :smiling_imp:"
            elif 'øl' in im:
                ud = get_user_display(user)
                bot_text = "{}. Mente du: {}?".format(ud, replace_keep_case("øl", "rosé", text))
            elif 'fredag' in im:
                if datetime.datetime.now().weekday() == 4:
                    bot_text = "I dag er det fredag. :wine_glass: SKÅL :wine_glass:"
                else:
                    bot_text = "Det er ikke fredag i dag"
            elif 'skål' in im:
                bot_text = ' :wine_glass: SKÅL {} :wine_glass:'.format(get_user_display(user))
            else:
                print("no?", sim)

            if bot_text:
                Client.api_call(method='chat.postMessage',
                                channel=channel,
                                text=bot_text)


            if 'rose' in sim and '?' in im:

                r = requests.get('https://www.yr.no/sted/Danmark/Nordjylland/%C3%85lborg/forecast.xml')
                root = ET.fromstring(r.content)
                forecast = root.find('forecast').find('tabular').find('time')
                temp = forecast.find('temperature').get('value')
                symbol = forecast.find('symbol').get('name')

                ud = get_user_display(user)
                bot_text = '{}°C {}. {} {}.'.format(temp, symbol, get_rose_message(), ud)
                Client.api_call(method='chat.postMessage',
                                channel=channel,
                                #icon_url='http://lorempixel.com/48/48',
                                text=bot_text)
                Client.api_call(
                    "reactions.add",
                    channel=channel,
                    name="wine_glass",
                    timestamp=timestamp
                )

                return Response(status=status.HTTP_200_OK)

        return Response(status=status.HTTP_200_OK)



class Vejr(APIView):
    def get(self, request, *args, **kwargs):
        r = requests.get('https://www.yr.no/sted/Danmark/Nordjylland/%C3%85lborg/forecast.xml')
        root = ET.fromstring(r.content)
        forecast = root.find('forecast').find('tabular').find('time')
        temp = forecast.find('temperature')
        symbol = forecast.find('symbol')

        return Response(status=status.HTTP_200_OK)
