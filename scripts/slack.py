import argparse
import os
import sys
import yaml

from slack_sdk import WebClient

import logging

log = logging.getLogger('slack')

def main():
    """
    Send message to Slack channels or users.
    """
    parser = argparse.ArgumentParser(
        description="Send a message to Slack channels")
    parser.add_argument('channels', metavar='str', nargs='+',
        help='Channels where the message to be sent, use @ for user name lookup')
    parser.add_argument('--settings',
        default=os.environ.get('HOME') + '/.config/slack_sdk/settings.yaml',
        help='Path to yaml file with slack_sdk settings')
    parser.add_argument('-m', '--message', default=sys.stdin, type=argparse.FileType('r'),
        help='Path to the file with message text to be sent')
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
    else:
        log.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)

    with open(args.settings) as f:
        log.debug(f'Read settings from "args.settings"')
        settings = yaml.safe_load(f)

    message = args.message.read()
    client = WebClient(token=settings.get('token'))
    users = None
    for c in args.channels:
        if '@' in c:
            users = users or client.users_list()
            if c.startswith('@'):
                user_name = c[1:]
            else:
                # looks like email
                user_name = c
            try:
                user = next(_ for _ in users['members']
                                        if _['name'] == user_name
                                        or user_name == _.get('profile', {}).get('display_name', None)
                                        or user_name == _.get('profile', {}).get('real_name', None)
                                        or user_name == _.get('profile', {}).get('email', None))
                user_id = user['id']
                log.debug(f'Found user "{user_name}" with id "{user_id}"')
                log.debug(f'All data: {user}')
            except Exception as e:
                log.error(f'Cannot find user with such name, '
                            f'display name, real name or email: "{user_name}"')
                variants = [_['name'] for _ in users['members']
                    if user_name.lower() in _['name'].lower()
                    or user_name.lower() in _.get('profile', {}).get('display_name', '').lower()
                    or user_name.lower() in _.get('profile', {}).get('real_name', '').lower()
                    or user_name.lower() in _.get('profile', {}).get('email', '').lower()]
                if variants:
                    log.error(f'Maybe you need one of the following: {variants}')
                continue
            channel = user_id
        else:
            channel = f'#{c}'
        client.chat_postMessage(channel=channel, text=message)


if __name__ == "__main__":
    main()

