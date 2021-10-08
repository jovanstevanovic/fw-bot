#!/usr/bin/python3
import asyncio
import enum
import json
import time
from datetime import datetime
from json import JSONDecodeError

from telethon import TelegramClient

# Global variables
from telethon.errors import PeerFloodError

CONFIG_FILE = "configuration.json"
API_ID = 1370903
API_HASH = '23c73e7bb6075cd2c909ca51decd7460'
BUFFER_SIZE = 10


# Message type.
class MessageType(enum.Enum):
    INFO = "[INFO]"
    ERROR = "[ERR0]"
    WARN = "[WARN]"
    SPEC = "[SPEC]"
    NO_HEADER = ""


# Print functions.
def print_message(message, t):
    if t == MessageType.INFO:
        print('\033[1;39m' + t.value + " " + message + '\033[0m')  # default
        return
    if t == MessageType.ERROR:
        print('\033[1;31m' + t.value + " " + message + '\033[0m')  # red
        return
    if t == MessageType.WARN:
        print('\033[1;33m' + t.value + " " + message + '\033[0m')  # yellow
        return
    if t == MessageType.SPEC:
        print('\033[1;32m' + t.value + " " + message + '\033[0m')  # green
        return
    print(message)


# File utils.
def read_json_file(filename):
    try:
        with open(filename) as input_file:
            return json.load(input_file)
    except IOError:
        print_message("Input file {} is missing or deleted!".format(filename), MessageType.ERROR)
        exit(1)
    except JSONDecodeError as err:
        print_message("Bad JSON syntax: {}".format(err), MessageType.ERROR)
        exit(1)


def filter_groups(groups, criteria):
    entity = list(filter(lambda e: e.title == criteria, groups))
    if len(entity) == 0:
        print_message("Group not found!", MessageType.ERROR)
        exit(2)
    else:
        return entity[0]


def remove_tag(m):
    m.message = m.message.replace("Published By: @last_satoshi", "")  # Tag removal needs improvement.
    return m


def filter_new_messages(refresh_rate, current_messages):
    now = datetime.now(current_messages[0].date.tzinfo)  # timezone is same for all messages of one channel.
    new_messages = list(filter(
        lambda m: m.message is not None and m.message != '' and abs((now - m.date).total_seconds()) < refresh_rate,
        current_messages))
    new_messages = list(map(remove_tag, new_messages))
    new_messages.reverse()
    return new_messages


async def run(refresh_rate, client, source_group, target_group):
    while True:
        source_messages = await client.get_messages(source_group, BUFFER_SIZE)
        if len(source_messages) == 0:
            print_message("Fetching message failed!", MessageType.ERROR)
            exit(3)

        new_messages = filter_new_messages(refresh_rate, source_messages)
        try:
            for new_message in new_messages:
                await client.send_message(target_group, new_message.message)
        except PeerFloodError:
            print_message("Too many messages sent in same time!", MessageType.WARN)
        time.sleep(refresh_rate)


async def start_daemon(index, refresh_rate, client, group):
    print_message("Starting daemon {}...".format(index), MessageType.INFO)

    groups = await client.get_dialogs()
    source_group, target_group = filter_groups(groups, group['source_group']), filter_groups(groups,
                                                                                             group['target_group'])
    try:
        await run(refresh_rate, client, source_group, target_group)
    except KeyboardInterrupt:
        print_message("Starting daemon {}...done".format(index), MessageType.INFO)


async def do(configuration):
    print_message("Connecting user...", MessageType.INFO)

    phone = configuration['phone']
    async with TelegramClient(phone, API_ID, API_HASH) as client:
        await client.connect()
        is_authorized = await client.is_user_authorized()
        if not is_authorized:
            client.send_code_request(phone)
            client.sign_in(phone, input('Enter the code: '))
        print_message("Connecting user...done", MessageType.INFO)

        await asyncio.gather(*(start_daemon(index, configuration['refresh_rate'], client, group) for index, group in
                               enumerate(configuration['groups'])))


def main():
    print_message("Turn off 2FA, if it's enabled!", MessageType.SPEC)

    configuration = read_json_file(CONFIG_FILE)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(do(configuration))
    loop.close()

    print_message("Script ended successfully!", MessageType.SPEC)


if __name__ == '__main__':
    main()
