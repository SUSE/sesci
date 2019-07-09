#!/usr/bin/env python
# Create ovh server
import os
import os.path
import yaml
import time
import paramiko
import logging
import socket
import json
import sys
import docopt
import fcntl
import base64

import openstack
import traceback

doc = """
Usage:
    os-server --action <action> [options]

Allocate node in openstack, provision it, or delete

Options:

  -a <action>, --action <action>        create, provision, delete action
  -s <status>, --status <status>        path to status file [default: .os_server_status.json]
  -t <target>, --target <target>        overrides target name
  -f <target>, --spec-file <spec-file>  path to a spec file, optional
  -d, --debug                           debug mode
"""

args = docopt.docopt(doc, argv=sys.argv[1:])

if args.get('--debug'):
    openstack.enable_logging(debug=True)


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
    'userdata': 'openstack/user-data.yaml',
    'keyfile':   secret_file, 
    'keyname': 'storage-automation',
    'networks': ['Ext-Net'],
    'vars': {
        'dependencies': ['git', 'java', 'ccache'],
    }
}

spec_path = args.get('--spec-file')
if spec_path:
    with open(spec_path, 'r') as f:
        if spec_path.endswith('.yaml') or spec_path.endswith('.yml'):
            server_spec = yaml.safe_load(f)
        else:
            server_spec = json.load(f)
        def override_dict(obj, key, env=None, default=None):
            if env and env in os.environ:
                obj[key] = os.environ.get(env, default)
            elif default:
                obj[key] = default
        override_dict(server_spec, 'keyfile', env='SECRET_FILE')
        override_dict(server_spec, 'name', default=target_mask)
        override_dict(server_spec, 'flavor', default=target_flavor)

print(json.dumps(server_spec, indent=2))

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
                            print("Process", os.getpid(), "waits", lock_wait, "seconds...")
                            time.sleep(lock_wait)
                    else:
                            raise SystemExit('Unable to obtain file lock: %s' % lockfile)
    
def set_server_name(server_id):
    print("Update name for server %s" % server_id)
    server_list = conn.compute.servers()
    existing_servers = [i.name for i in server_list]
    for n in range(99):
        try:
          target = target_mask % n
        except:
          target = target_mask
        if not target in existing_servers:
            print("Setting server name to %s" % target)
            #conn.compute.update_server(server_id, name=target)
            #s = conn.update_server(server_id, name=target)
            c.update_server(server_id, name=target)

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
    
def host_client(hostname, identity):
    """
        returns ssh client object
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    wait = 10
    timeout = 300
    start_time = time.time()
    print("Connecting to host [" + hostname + "]")
    while True:
        try:
            client.connect(hostname, username=server_spec['username'], key_filename=identity)
            print("Connected to the host " + hostname)
            break
        except (paramiko.ssh_exception.NoValidConnectionsError, socket.error) as e:
            print("Exeption occured: " + str(e))
            if timeout < (time.time() - start_time):
                print("ERROR: Timeout occured")
                raise e
            else:
                print("Waiting " + str(wait) + " seconds...")
                time.sleep(wait)
    return client

def provision_host(hostname, identity):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    timeout = 300 
    wait = 10
    start_time = time.time()
    print("Connecting to host [" + hostname + "]")
    while True:
        try:
            client.connect(hostname, username=server_spec['username'], key_filename=identity)
            print("Connected to the host " + hostname)
            break
        except (paramiko.ssh_exception.NoValidConnectionsError, socket.error) as e:
            print("Exeption occured: " + str(e))
            if timeout < (time.time() - start_time):
                print("ERROR: Timeout occured")
                raise e
            else:
                print("Waiting " + str(wait) + " seconds...")
                time.sleep(wait)
    provision_node(client)

def client_run(client, command_list):
    for command in command_list:
      print("+ " + command)
      stdin, stdout, stderr = client.exec_command(command)
      while True:
        l = stdout.readline()
        if not l:
          break
        print(">>> " + l.rstrip())

def host_run(host, command_list):
    cli = host_client(host, secret_file)
    client_run(cli, command_list)

def provision_node(client):
    target_fqdn = status['server']['name'] + ".suse.de"
    target_addr = status['server']['ip']
    command_list = [
      'sudo zypper --no-gpg-checks ref 2>&1',
      'sudo zypper install -y %s 2>&1' % ' '.join(server_spec['vars']['dependencies']),
      'echo "' + target_addr + '\t' + target_fqdn + '" | sudo tee -a /etc/hosts',
      'sudo hostname ' + target_fqdn,
      'cat /etc/os-release',
      ]
    if 'copy' in server_spec:
        print("Copying file to host...")
        copy_files(client, server_spec['copy'])
    client_run(client, command_list)
    if 'exec' in server_spec:
        client_run(client, server_spec['exec'])

def copy_files(client, copy_spec):
    if copy_spec:
        with client.open_sftp() as sftp:
            for i in copy_spec:
                for path in i['from']:
                    if not path.startswith('/'):
                        if not os.path.isfile(path):
                            base = os.path.dirname(__file__)
                            if base:
                                path = base + '/' + path
                    path = os.path.abspath(path)
                    print('Upload file %s' % path)
                    name = os.path.basename(path)
                    dest = i['into'].rstrip('/') + '/' + name
                    sftp.put(path, dest)
                    for x in ['mode', 'chmod']:
                        if x in i:
                            sftp.chmod(dest, int(i[x], 8))

def create_server(image, flavor, key_name, user_data=None):
    print("Creating target using flavor %s" % flavor)
    print("Image=%s" % image.name)
    print("Data:\n%s" % user_data)
    #if user_data:
    #    user_data=base64.b64encode(user_data.encode('utf-8')).decode('utf-8')
    #target = conn.compute.create_server(
    #    name=status['server']['name'],
    #    image_id=image.id,
    #    flavor_id=flavor.id,
    #    key_name=key_name,
    #    user_data=user_data,
    #)
    target = conn.create_server(
        name=status['server']['name'],
        image=image.id,
        flavor=flavor.id,
        key_name=key_name,
        userdata=user_data,
    )
    print("Created target: %s" % target.id)
    update_server_status(id=target.id)
    print(target)
    # for some big nodes sometimes rename does not happen
    # and some pause is required for doing this
    grace_wait = 5
    print("Graceful wait %s sec before rename..." % grace_wait)
    time.sleep(grace_wait)
    set_name(target.id)

    try:
        timeout = 8 * 60
        wait = 10
        target_id = target.id
        start_time = time.time()
        while target.status != 'ACTIVE':
          print("STATUS:%s" % target.status)
          if target.status == 'ERROR':
            # only get_server_by_id can return 'fault' for a server
            x=conn.get_server_by_id(target_id)
            if 'fault' in x and 'message' in x['fault']:
                raise Exception("Server creation unexpectedly failed with message: %s" % x['fault']['message'])
            else:
                raise Exception("Unknown failure while creating server: %s" % x)
          if timeout > (time.time() - start_time):
            print('Server [' + target.name + '] is not active. waiting ' + str(wait) + ' seconds...')
            time.sleep(wait)
          else:
            print("ERROR: Timeout occured, was not possible to make server active")
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
        if not args.get('--debug'):
            print("Cleanup...")
            c.delete_server(target.id)
        exit(1)

if action in ['provision']:
    with open(status_path, 'r') as f:
        status = json.load(f)
        print(status)
    target_id = status['server']['id']
    target_ip = status['server']['ip']
    print("Provisioning target %s" % status['server']['name'])
    provision_host(target_ip, secret_file)
    exit(0)

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

    print("Looking up image %s... " % server_spec['image'],)
    image  = next((x for x in conn.image.images()
                    if x.name==server_spec['image']), None)
    if not image:
        raise Exception("Can't find image %s" % server_spec['image'])
    print("found %s" % image.id)
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
    userdata = None
    if 'userdata' in server_spec:
        path = server_spec['userdata']
        if not path.startswith('/'):
            base = os.path.dirname(__file__)
            if base:
                path = base + '/' + path
        with open(path, 'r') as f:
            userdata=f.read()
    create_server(image, flavor, keypair.name, userdata)
    exit(0)

