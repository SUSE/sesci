#!/usr/bin/env python
# Create ovh server
import os
import yaml
import time
import paramiko
import logging
import socket
import json
import sys
import docopt
import fcntl

import openstack
import traceback

#openstack.enable_logging(debug=True)

doc = """
Usage:
    os-server --action <action> [options]

Allocate node in openstack, provision it, or delete

Options:

  -a <action>, --action <action>        create, provision, delete action
  -s <status>, --status <status>        path to status file [default: .os_server_status.json]
  -t <target>, --target <target>        overrides target name
"""

args = docopt.docopt(doc, argv=sys.argv[1:])
action = args.get('--action')

if action not in ['create', 'delete']:
    print("ERROR: Wrong action '%s'" % action)
    raise Exeption("Wrong action '%s'" % action)

home = os.environ.get('HOME')
status_path   = args.get('--status')
target_mask   = args.get('--target') or os.environ.get('TARGET_MASK', 'mkck%02d')
target_user   = os.environ.get('TARGET_USER', 'opensuse')
target_limit  = os.environ.get('TARGET_LIMIT', 24)
target_image  = os.environ.get('TARGET_IMAGE', 'opensuse-42-3-jeos-pristine')
target_flavor = os.environ.get('TARGET_FLAVOR', 's1-2') #'b2-30')
secret_file   = os.environ.get('SECRET_FILE', home + '/.ssh/id_rsa')

conn = openstack.connect()

server_spec = {
    'flavor':   target_flavor,
    'name':     target_mask,
    'image':    target_image,
    'username': target_user,
    'keyfile':   secret_file, 
    'keyname': 'storage-automation',
    'networks': ['Ext-Net'],
    'vars': {
        'dependencies': ['git', 'java', 'ccache'],
    }
}

status = {
  'server': {
    'name': 'ci-target',
    'id': None,
    'ip': None,
  },
  'spec': server_spec,
}


def update_server_status(**kwargs):
    if kwargs:
        print(kwargs)
    for k,v in kwargs.items():
        print('override %s with %s' % (k,v))
        status['server'][k] = v
    print("Saving status to '%s'" % status_path)
    with open(status_path, 'w') as f:
        json.dump(status, f, indent=2)

def set_name(server_id):
    lockfile = '/tmp/' + target_mask
    lock_timeout = 5 * 60
    lock_wait = 2
    print("Trying to lock file for process " + str(os.getpid()))
    while True:
            try:
                    lock = open(lockfile, 'w')
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    print("File locked for process", os.getpid())
                    res = set_server_name(server_id)
                    fcntl.flock(lock, fcntl.LOCK_UN)
                    print("Unlocking for", str(os.getpid()))
                    break
            except IOError as err:
                    # print "Can't lock: ", err
                    if lock_timeout > 0:
                            lock_timeout -= lock_wait
                            print "Process", os.getpid(), "waits", lock_wait, "seconds..."
                            time.sleep(lock_wait)
                    else:
                            raise SystemExit('Unable to obtain file lock: %s' % lockfile)
    
def set_server_name(server_id):
    server_list = conn.compute.servers()
    existing_servers = [i.name for i in server_list]
    for n in range(99):
        try:
          target = target_mask % n
        except:
          target = target_mask
        if not target in existing_servers:
            conn.compute.update_server(server_id, name=target)
            return target
    print("ERROR: Can't allocate name")
    print("TODO: Add wait loop for name allocation")

def provision_server():
    ip = status['server']['ip']
    provision_host(ip, secret_file)


if action in ['provision']:
    provision_server()
     
c = conn.compute

def delete_server(target_id):
    print("Delete server with id '%s'" % target_id)
    try:
        target=c.get_server(target_id)
        c.delete_server(target.id)
    except Exception as e:
        print("WARNING: %s" % e)
    

def provision_host(hostname, identity):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    timeout = 300 
    wait = 10
    print "Connecting to host [" + hostname + "]" 
    while True:
        try:
            client.connect(hostname, username=server_spec['username'], key_filename=identity)
            print "Connected to the host " + hostname
            break
        except (paramiko.ssh_exception.NoValidConnectionsError, socket.error) as e:
            print "Exeption occured: " + str(e)
            if timeout < 0:
                print "ERROR: Timeout occured"
                raise e
            else:
                print "Waiting " + str(wait) + " seconds..."
                timeout -= wait
                time.sleep(wait)
    provision_node(client)

def provision_node(client):
    target_fqdn = status['server']['name'] + ".suse.de"
    target_addr = status['server']['ip']
    command_list = [
      'sudo zypper --no-gpg-checks ref 2>&1',
      'sudo zypper install -y %s 2>&1' % ' '.join(server_spec['vars']['dependencies']),
      'echo "' + target_addr + '\t' + target_fqdn + '" | sudo tee -a /etc/hosts',
      'sudo hostname ' + target_fqdn
      ]
    for command in command_list:
      print "+ " + command
      stdin, stdout, stderr = client.exec_command(command)
      while True:
        l = stdout.readline()
        if not l:
          break
        print ">>> " + l.rstrip()

def create_server(image, flavor, key_name):
    target = conn.compute.create_server(
        name=status['server']['name'],
        image_id=image.id,
        flavor_id=flavor.id,
        key_name=key_name,
    )
    print("Created target: %s" % target.id)
    update_server_status(id=target.id)
    print(target)
    try:
        set_name(target.id)

        timeout = 8 * 60
        wait = 10
        target_id = target.id
        while target.status != 'ACTIVE':
          print("STATUS:%s" % target.status)
          if timeout > 0: 
            print 'Server [' + target.name + '] is not active. waiting ' + str(wait) + ' seconds...'
            timeout -= wait
            time.sleep(wait)
          else:
            print "ERROR: Timeout occured, was not possible to make server active"
            break
          target=c.get_server(target_id)

        for i,v in target.addresses.items():
            print(i)
            print(v)

        ipv4=[x['addr'] for i, nets in target.addresses.items()
            for x in nets if x['version'] == 4][0]
        print(ipv4)
        update_server_status(ip=ipv4, name=target.name)
        provision_server()
    except:
        print("ERROR: Failed to create node")
        traceback.print_exc()
        print("Cleanup...")
        c.delete_server(target.id)

if action in ['delete']:
    with open(status_path, 'r') as f:
        status = json.load(f)
        print(status)
    target_id = status['server']['id']
    delete_server(target_id)
    exit(0)

if action in ['create']:
    server_list = c.servers()
    print("SERVERS: %s" % ", ".join([i.name for i in server_list]))

    image  = next(x for x in conn.image.images()
                    if x.name==server_spec['image'])
    flavor = next(x for x in c.flavors()
                    if x.name==server_spec['flavor'])
    flavors = sorted(i.name for i in c.flavors())
    #for i in flavors:
    #    print("FLAVOR: %s" % i)
    print("FLAVORS: %s" % ', '.join(flavors))
    f = c.find_flavor(server_spec['flavor'])
    print('Found flavor: %s' % f.name)
    keypair = conn.compute.find_keypair(server_spec['keyname'])
    print("Image:   %s" % image.name)
    print("Flavor:  %s" % flavor.name)
    print("Keypair: %s" % keypair.name)
    create_server(image, flavor, keypair.name)


