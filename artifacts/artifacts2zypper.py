#/usr/bin/python3

"""
A script to take a artifacts.yaml file as input and adds the corresponding
zypper repositories to the current system
"""


import argparse
import subprocess
import yaml


def _zypper_add_repos(repo_uri, repo_name):
    cmd = ['zypper', '-n', 'addrepo', '--no-gpgcheck',
           '--enable', '--refresh', repo_uri]
    if repo_name:
        cmd += [repo_name]
    subprocess.check_call(cmd)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'artifact', help='A artifacts yaml file')
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    with open(args.artifact, 'r') as f:
        data = yaml.safe_load(f.read())
        if not data.get('artifacts'):
            raise Exception('Not found "artifacts" map. Not a valid artifacts file')
        for repo_name, repo_data in data['artifacts'].items():
            if not repo_data.get('url'):
                print('No "url" found for repo "{}". Skipping'.format(repo_name))
                continue
            _zypper_add_repos(repo_data['url'], repo_name)
