#!/usr/bin/env python
# Create ovh server
import argparse
import os
import os.path
import yaml
import time
import paramiko
import logging
import socket
import json
import signal
import sys
import fcntl
import base64
import jinja2

import openstack
import traceback

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', help='run, create/delete actions',
                        choices=['create', 'delete', 'provision', 'run'])
    parser.add_argument('-s', '--status', help='path to status file (default: %(default)s)',
                        default='.os_server_status.json')
    parser.add_argument('-t', '--target', help='overrides target name. (default: %(default)s)',
                        default=os.environ.get('TARGET_MASK', '')) # mkck%02d
    parser.add_argument('-f', '--spec-file', help='path to a spec file, optional')
    parser.add_argument('-d', '--debug', help='debug mode', action='store_true')
    parser.add_argument('-k', '--keep-nodes', help='do not cleanup resource', action='store_true')
    return parser.parse_args()

args = parse_args()

if args.debug:
    openstack.enable_logging(debug=True)


home = os.environ.get('HOME')
target_user   = os.environ.get('TARGET_USER', 'opensuse')
target_image  = os.environ.get('TARGET_IMAGE', 'opensuse-42-3-jeos-pristine')
target_flavor = os.environ.get('TARGET_FLAVOR', '') #'s1-2', 'b2-30')
secret_file   = os.environ.get('SECRET_FILE', home + '/.ssh/id_rsa')
target_network  = os.environ.get('TARGET_NETWORK', None)
target_floating = os.environ.get('TARGET_FLOATING', None)

conn = openstack.connect()

server_spec = {
    'flavor':   target_flavor,
    'name':     args.target or 'target%02d',
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

if args.spec_file:
    with open(args.spec_file, 'r') as f:
        if args.spec_file.endswith('.yaml') or args.spec_file.endswith('.yml'):
            server_spec = yaml.safe_load(f)
        else:
            server_spec = json.load(f)
        def override_dict(obj, key, env=None, default=None):
            if env and env in os.environ:
                obj[key] = os.environ.get(env, default)
            elif default:
                obj[key] = default
        override_dict(server_spec, 'keyfile', env='SECRET_FILE')
        override_dict(server_spec, 'image', env='TARGET_IMAGE')
        override_dict(server_spec, 'name', default=args.target)
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
    print("Saving status to '%s'" % args.status)
    with open(args.status, 'w') as f:
        json.dump(status, f, indent=2)

def set_name(server_id):
    lockfile = '/tmp/' + server_spec['name']
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

def make_server_name(t, n):
    """
    Returns name based on the template and numeric index.

    The template can contain one placeholder for the index.
    If template does not contain any placeholder,
    then treat template as a bare name, and return it.

    :param t: an str with name template, for example: node%00d
    :param n: an int value with numeric index.
    """
    try:
      target = t % n
    except:
      target = t
    return target

def set_server_name(server_id):
    print("Update name for server %s" % server_id)
    server_list = conn.compute.servers()
    existing_servers = [i.name for i in server_list]
    for n in range(99):
        target = make_server_name(server_spec['name'], n)
        if not target in existing_servers:
            print("Setting server name to %s" % target)
            #conn.compute.update_server(server_id, name=target)
            #s = conn.update_server(server_id, name=target)
            tries=20
            while tries > 0:
                conn.compute.update_server(server_id, name=target)
                time.sleep(10) # wait count to 10
                s=conn.get_server_by_id(server_id)
                if s.name and s.name == target:
                    break
                else:
                    print("Server name is '%s', should be '%s'" %(s.name, target))
                tries -= 1
                print("Left %s tries to rename the server" % tries)
            else:
                raise SystemExit("Cannot set name to '%s' for server '%s'" % (target, server_id))
            return target
    print("ERROR: Can't allocate name")
    print("TODO: Add wait loop for name allocation")

def provision_server():
    ip = status['server']['ip']
    provision_host(ip, secret_file)

if args.action in ['provision']:
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
            print("Exception occured: " + str(e))
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
    provision_node(client, hostname=hostname)

def render_command(command, env=os.environ):
    return jinja2.Template(command).render(env)

def client_run(client, command_list, hostname=None, env=[]):
    for c in command_list:
      name = None
      if isinstance(c, str):
          if c == 'reboot':
              name = 'rebooting node'
              command = 'sudo reboot &'
          elif c == 'wait_host':
              client = host_client(hostname, secret_file)
              continue
          else:
              command = render_command(c)
      if isinstance(c, dict):
          command = render_command(c.get('command'))
          name = c.get('name', None)
      if name:
          print(f"=== {name}")
      for i in command.split('\n'):
          print("+ " + i)
      stdin, stdout, stderr = client.exec_command(command)
      while True:
        l = stdout.readline()
        if not l:
          break
        print(">>> " + l.rstrip())
      exit_code = stdout.channel.recv_exit_status()
      if exit_code:
          raise Exception(f"Received exit code {exit_code} while running command: {command}")
      print(f"||| exit code: {exit_code}")

def host_run(host, command_list):
    cli = host_client(host, secret_file)
    client_run(cli, command_list, hostname=host)

def provision_node(client, hostname=None):
    target_fqdn = status['server']['name'] + ".suse.de"
    target_addr = status['server']['ip']
    command_list = []
    if server_spec.get('vars') and server_spec['vars'].get('dependencies'):
        command_list += [
            'sudo zypper --no-gpg-checks ref 2>&1',
            'sudo zypper install -y %s 2>&1' % ' '.join(server_spec['vars']['dependencies']),
        ]
    command_list += [
      'echo "' + target_addr + '\t' + target_fqdn + '" | sudo tee -a /etc/hosts',
      'sudo hostname ' + target_fqdn,
      'cat /etc/os-release',
      ]
    if 'copy' in server_spec:
        print("Copying file to host...")
        copy_files(client, server_spec['copy'])
    client_run(client, command_list, hostname=hostname)
    if 'exec' in server_spec:
        client_run(client, server_spec['exec'], hostname=hostname)

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

def _create_server(image, flavor, key_name, user_data=None):
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

    # if the target is not kind a template, just use it as server name
    target_mask = server_spec['name']
    rename_server = (target_mask != make_server_name(target_mask, 0))
    if rename_server:
        target_name = status['server']['name']
    else:
        target_name = target_mask
    update_server_status(name=target_name)

    params  = dict(
        name=target_name,
        image=image.id,
        flavor=flavor.id,
        key_name=key_name,
        userdata=user_data,
    )

    if target_network:
        params['network'] = target_network

    target = conn.create_server(**params)
    target_id = target.id
    print("Created target: %s" % target.id)
    update_server_status(id=target.id)
    print(target)

    fip_id = None
    try:
        if rename_server:
            # for some big nodes sometimes rename does not happen
            # and a pause is required
            grace_wait = 5
            print("Graceful wait %s sec before rename..." % grace_wait)
            time.sleep(grace_wait)
            set_name(target.id)

        timeout = 8 * 60
        wait = 10
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
        if target_floating:
            faddr = conn.create_floating_ip(
                    network=target_floating,
                    server=target,
                    fixed_address=ipv4,
                    wait=True,
                    )
            ipv4 = faddr['floating_ip_address']
            fip_id = faddr['id']
            update_server_status(fip_id=fip_id)

        update_server_status(ip=ipv4, name=target.name)
        provision_server()
    except:
        print("ERROR: Failed to create node")
        traceback.print_exc()
        if not args.debug and not args.keep_nodes:
            print("Cleanup...")
            if target_floating:
                if fip_id:
                    conn.delete_floating_ip(fip_id)
            c.delete_server(target.id)
        exit(1)

if args.action in ['provision']:
    with open(status_path, 'r') as f:
        status = json.load(f)
        print(status)
    target_id = status['server']['id']
    target_ip = status['server']['ip']
    print("Provisioning target %s" % status['server']['name'])
    provision_host(target_ip, secret_file)
    exit(0)

def do_delete():
    with open(args.status, 'r') as f:
        status = json.load(f)
        print(status)
    target_id = status['server']['id']
    fip_id = status['server'].get('fip_id')
    delete_server(target_id)
    if fip_id:
        conn.delete_floating_ip(fip_id)

def do_create():
    server_list = c.servers()
    print("SERVERS: %s" % ", ".join([i.name for i in server_list]))

    print("Looking up image %s... " % server_spec['image'],)
    image = conn.get_image(server_spec['image'])
    if not image:
        raise Exception("Can't find image %s" % server_spec['image'])
    print("found %s" % image.id)
    flavor = conn.get_flavor(server_spec['flavor'])
    if not flavor:
        raise Exception("Can't find flavor %s" % server_spec['flavor'])
    print('Found flavor: %s' % flavor.id)
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
    _create_server(image, flavor, keypair.name, userdata)

def handle_signal(signum, frame):
    print("Handling signal", signum)
    # Instead of calling do_delete() we raise SystemExit exception so
    # corresponding catch can do cleanup for us if required
    raise(SystemExit)

if args.action in ['delete']:
    do_delete()

signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

if args.action in ['create']:
    do_create()

if args.action in ['run']:
    do_create()
    if not args.keep_nodes:
        do_delete()

exit(0)
