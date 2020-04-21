# the following line should be at the beginning
from __future__ import print_function

import sys, yaml

dest_file = sys.argv[1]
dest_keys = sys.argv[2]
src_file  = sys.argv[3]

if len(sys.argv) > 4:
    src_keys = sys.argv[4]
else:
    src_keys = ''

print(sys.argv, file=sys.stderr)

def set_key(k, v, h):
    if len(k) > 1:
        if k[0] not in h:
            h[k[0]] = {}
        set_key(k[1:], v, h[k[0]])
    else:
        h[k[0]] = v

def get_key(h, k):
    if k:
        if k[0] in h:
            hk=h[k[0]]
            return get_key(hk, k[1:]) if len(k) > 1 else hk
        else:
            return None
    else:
        return h
def copy_yaml(dest, keys, src, src_keys=''):
    with open(dest, 'r') as d:
        data = yaml.safe_load(d)
        with open(src_file, 'r') as s:
            a = yaml.safe_load(s)
            v = get_key(a, src_keys.split(':')) if src_keys else a
            set_key(keys.split(':'), v, data)
        return data

data = copy_yaml(dest_file, dest_keys, src_file, src_keys)
print(yaml.safe_dump(data, default_flow_style=False))
