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

Client = SlackClient(settings.SLACK_BOT_USER_TOKEN)

def replace_keep_case(word, replacement, text):
    def func(match):
        g = match.group()
        if g.islower():
            return replacement.lower()
        if g.istitle():
            return replacement.title()
        if g.isupper():
            return replacement.upper()
        return replacement
    return re.sub(word, func, text, flags=re.I)


def get_rose_message():
    rose_messages = [
        'Det er pissefint rosévejr',
        'Det bliver ikke bedre',
        'Rosébowling?'
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


def time_until(event_datetime):
    now = datetime.datetime.now()
    delta = event_datetime - now
    if event_datetime < now:
        return {}
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds // 60) % 60
    return {
        'days': days,
        'hours': hours,
        'minutes': minutes
    }

def handle_event_message(event_message):
    # process user's message
    user = event_message.get('user')
    text = event_message.get('text')
    channel = event_message.get('channel')
    timestamp = event_message.get('ts')

    im = text.lower()
    sim = slugify(text.lower())

    bot_text = ''
    if 'polen' in sim:
        polen = datetime.datetime(2018, 5, 10, 10, 0, 0)
        timeleft = time_until(polen)
        if timeleft:
            bot_text = ('Der er {} dage, {} timer og {} minutter til Polen').format(
                timeleft['days'], timeleft['hours'], timeleft['minutes'])
        else:
            bot_text = ':flag-pl: POLEN!!! :flag-pl:'
    elif 'stax' in im:
        bot_text = "'Stax players are agents of Satan' - Hitler 1997 :smiling_imp:"
    elif 'øl' in im:
        ud = get_user_display(user)
        bot_text = "{}. Mente du: {}?".format(ud, replace_keep_case("øl", "rosé", text))
    elif 'fredag' in im:
        if datetime.datetime.now().weekday() == 4:
            bot_text = "I dag er det fredag. :wine_glass: SKÅL :wine_glass:"
        else:
            next_friday = datetime.datetime.now()
            while next_friday.weekday() != 4:
                next_friday += datetime.timedelta(1)
            next_friday = next_friday.replace(hour=0, minute=00) - datetime.timedelta(hours=2)
            timeleft = time_until(next_friday)
            bot_text = 'Det er ikke fredag i dag. Der er {} dage, {} timer og {} minutter til fredag'.format(timeleft['days'], timeleft['hours'], timeleft['minutes'])
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
