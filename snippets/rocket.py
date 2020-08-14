import argparse
import os
import sys
import yaml

from rocketchat.api import RocketChatAPI

def main():
    parser = argparse.ArgumentParser(
        description="Send a message to RocketChat channels"
        )
    parser.add_argument('channels', metavar='str', nargs='+',
        help='Channels where the message to be sent')
    parser.add_argument('--settings',
        default=os.environ.get('HOME') + '/.config/rocketchat.api/settings.yaml',
        help='Path to yaml file with rocketchat.api settings')
    parser.add_argument('-m', '--message', default=sys.stdin, type=argparse.FileType('r'),
        help='Path to the file with message text to be sent')

    args = parser.parse_args()
    
    with open(args.settings) as f:
        settings = yaml.safe_load(f)

    message = args.message.read()
    rocket = RocketChatAPI(settings=settings)
    for channel in args.channels:
        rocket.send_message(message, channel)

if __name__ == "__main__":
    main()
