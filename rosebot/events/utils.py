import datetime
import random
import re
import xml.etree.ElementTree as ET
from random import randint

import requests
from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from slugify import slugify

import pokebase as pb
from slackclient import SlackClient

Client = SlackClient(settings.SLACK_BOT_USER_TOKEN)
AdminClient = SlackClient(settings.SLACK_OAUTH_ACCESS_TOKEN)

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
        'Rosébowling?',
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
        polen = datetime.datetime(2019, 5, 23, 13, 0, 0)
        timeleft = time_until(polen)
        if timeleft:
            bot_text = ('Der er {} dage, {} timer og {} minutter til Polen').format(
                timeleft['days'], timeleft['hours'], timeleft['minutes'])
        else:
            bot_text = ':flag-pl: POLEN!!! :flag-pl:'
    elif 'stax' in im:
        bot_text = "'Stax players are agents of Satan' - Hitler 1997 :smiling_imp:"
    elif 'peter madsen' in im:
        bot_text = "Peter Madsen did nothing wrong"
    elif 'øl' in im:
        better_msg = replace_keep_case("øl", "rosé", text)
        response = AdminClient.api_call(
            "chat.update",
            ts=timestamp,
            channel=channel,
            text=better_msg
        )
        if not response.get('ok'):
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
    elif 'pokemon' in im:
        random_pokemon = pb.pokemon(randint(1, 150))
        image_url = random_pokemon.sprites.front_default
        attachments = attachments = [{"title": random_pokemon.name.title(),
                                      "image_url": image_url}]

        Client.api_call(method='chat.postMessage',
                        text=f'A wild {random_pokemon.name.title()} appears',
                        channel=channel,
                        attachments=attachments)
    else:
        print("no?", sim)

    if bot_text:
        Client.api_call(method='chat.postMessage',
                        channel=channel,
                        text=bot_text)

    if 'rose' in sim and '?' in im:
        r = requests.get('https://www.yr.no/sted/Danmark/Nordjylland/%C3%85lborg/forecast.xml')
        root = ET.fromstring(r.content)
        forecast_tabs = root.find('forecast').find('tabular')

        forecasts = [forecast for forecast in forecast_tabs.findall('time')]
        forecast = forecasts[0]

        # Spaghetti incoming, please refactor frix
        if 'senere' in sim:
            forecast = forecasts[1]
        if 'morgen' in sim:
            # Det er så hax jeg magter ikke at fikse timezones rigtigt
            tomorrow = datetime.datetime.now() + datetime.timedelta(1)
            tomorrow = tomorrow.replace(hour=0, minute=00)
            # Find the next forecast from tomorrow noon
            for fc in forecasts:
                forecast_time = datetime.datetime.strptime(fc.get('from'), '%Y-%m-%dT%H:%M:%S')
                if forecast_time > tomorrow and fc.get('period') == '2': # period 2 is from 12:00 - 18:00
                    forecast = fc
                    break
        if 'polsemix' in sim:
            pølsemix = datetime.datetime(2019, 5, 23, 0, 0, 0)
            # Find the next forecast from tomorrow noon
            for fc in forecasts:
                forecast_time = datetime.datetime.strptime(fc.get('from'), '%Y-%m-%dT%H:%M:%S')
                if forecast_time > pølsemix and fc.get('period') == '2': # period 2 is from 12:00 - 18:00
                    forecast = fc
                    break

        temp = forecast.find('temperature').get('value')
        symbol = forecast.find('symbol').get('name')
        symbol_id = forecast.find('symbol').get('var')
        symbol_url = "http://51.15.50.78:8000/media/{0}.png".format(symbol_id)
        ud = get_user_display(user)
        bot_text = '{}°C {}. {} {}.'.format(temp, symbol, get_rose_message(), ud)
        Client.api_call(method='chat.postMessage',
                        channel=channel,
                        icon_url=symbol_url,
                        text=bot_text)
        Client.api_call(
            "reactions.add",
            channel=channel,
            name="wine_glass",
            timestamp=timestamp
        )
