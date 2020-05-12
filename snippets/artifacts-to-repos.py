#/usr/bin/python
#
# Convert artifacts to teuthology repos format
#
# usage: artifacts-to-repos <dest-yaml> <artifacts-yaml> [<artifacts-yaml> ...]
#

import sys, yaml

arts = sys.argv[1:]

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
    if 'src' in a:
        r['src'] = a['src']
    repos.append(r)
print(yaml.safe_dump(repos))
