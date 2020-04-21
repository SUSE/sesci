#/usr/bin/python
#
# usage: append-artifacts <dest-yaml> <artifacts-yaml> [<artifacts-yaml> ...]
#

import sys, yaml

dest = sys.argv[1]
arts = sys.argv[2:]

with open(dest) as f:
    y = yaml.safe_load(f)
repos = []
for i in arts:
  artifacts = yaml.safe_load(open(i))['artifacts']
  for name, a in artifacts.items():
    url = a['url']
    if '!' in name:
        n, p = name.split('!', 1)
        r = {'name': n, 'priority': int(p), 'url': url}
    else:
        r = {'name': name, 'url': url}
    repos.append(r)
if 'overrides' not in y:
    y['overrides'] = {}
if 'install' not in y['overrides']:
    y['overrides']['install'] = {}
if 'repos' not in y['overrides']['install']:
    y['overrides']['install']['repos'] = []
y['overrides']['install']['repos'] += repos
with open(dest, 'w') as f:
    yaml.safe_dump(y, f)
