import datetime
import random
import re
import xml.etree.ElementTree as ET
from random import randint

import requests

import pokebase as pb
from django.conf import settings
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from slackclient import SlackClient
from slugify import slugify

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
        'Rosébowling?',
        "Det er altid godt vejr i Polen",
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


def get_random_names(number):
    names = [
        'kasper',
        'allan',
        'jan',
        'kenneth',
        'kermie',
        'thies',
        'frix',
        'jeppe',
        'simon',
        'aske'
    ]

    random.shuffle(names)
    return names[:number]


def get_replacement_words():
    # Save these in DB at some point

    random_names = get_random_names(8)
    return {
        'øl': 'rosé',
        'smør': 'ost',
        'ost': 'smør',
        'corona': 'pest',
        random_names[0]: random_names[1],
        random_names[2]: random_names[3],
        random_names[4]: random_names[5],
        random_names[6]: random_names[7]
    }


def handle_event_message(event_message):
    # process user's message
    user = event_message.get('user')
    text = event_message.get('text')
    channel = event_message.get('channel')
    timestamp = event_message.get('ts')

    im = text.lower()
    sim = slugify(text.lower())

    replacement_words = get_replacement_words()

    bot_text = ''
    if 'polen' in sim or re.search("p+o+l+e+n+", sim):
        polen = datetime.datetime(2020, 9, 10, 10, 30, 0)
        timeleft = time_until(polen)
        if timeleft:
            dage = "dage"
            if timeleft['days'] == 1:
                dage = "dag"
            timer = "timer"
            if timeleft['hours'] == 1:
                timer = "time"
            minutter = "minutter"
            if timeleft['minutes'] == 1:
                minutter = "minut"

            if not timeleft['days'] and not timeleft['hours']:
                bot_text = ('Der er kun {} {} til POLEN!').format(timeleft['minutes'], minutter)
            elif not timeleft['days']:
                bot_text = ('Der er kun {} {} og {} {} til Polen').format(
                    timeleft['hours'], timer, timeleft['minutes'], minutter)
            else:
                bot_text = ('Der er {} {}, {} {} og {} {} til Polen').format(
                    timeleft['days'], dage, timeleft['hours'], timer, timeleft['minutes'], minutter)
        else:
            bot_text = ':flag-pl: POLEN!!! :flag-pl:'
    elif 'stax' in im:
        bot_text = "'Stax players are agents of Satan' - Hitler 1997 :smiling_imp:"
    elif 'peter madsen' in im:
        bot_text = "Peter Madsen did nothing wrong"
    elif any(word in im for word in replacement_words.keys()):
        # Could probably be done better with regex
        better_msg_words = []
        for word in text.split():
            some_better_word = word
            for bad_word, better_word in replacement_words.items():
                if bad_word in word.lower():
                    some_better_word = replace_keep_case(bad_word, better_word, word)
            better_msg_words.append(some_better_word)
        better_msg = ' '.join(better_msg_words)
        response = AdminClient.api_call(
            "chat.update",
            ts=timestamp,
            channel=channel,
            text=better_msg
        )
        if not response.get('ok'):
            ud = get_user_display(user)
            bot_text = "{}. Mente du: {}?".format(ud, better_msg)
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
        random_pokemon = pb.pokemon(randint(1, 802))
        image_url = random_pokemon.sprites.front_default
        attachments = attachments = [{"title": random_pokemon.name.title(),
                                      "image_url": image_url}]

        Client.api_call(method='chat.postMessage',
                        text='A wild {} appears'.format(random_pokemon.name.title()),
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
