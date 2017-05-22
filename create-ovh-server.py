# Create ovh server
import os
import yaml
import time

def get_nova_credentials_v2(yaml_file):
    d = {}
    with open(yaml_file) as y:
        c = yaml.load(y)
        d['username']    = c.get('OS_USERNAME')
        d['api_key']     = c.get('OS_PASSWORD')
        d['auth_url']    = c.get('OS_AUTH_URL')
        d['project_id']  = c.get('OS_TENANT_NAME')
        d['region_name'] = c.get('OS_REGION_NAME')
    d['version'] = '2'
    return d


from novaclient.client import Client

target_file   = os.environ.get('TARGET_FILE', 'target.properties')
target_mask   = os.environ.get('TARGET_MASK', 'mkck%02d')
target_limit  = os.environ.get('TARGET_LIMIT', 24)
target_image  = os.environ.get('TARGET_IMAGE', 'opensuse-42.2-x86_64')
target_flavor = os.environ.get('TARGET_FLAVOR', 'hg-15-ssd')
ovh_key       = os.environ.get('OVH_KEY', 'storage-automation')
ovh_conf      = os.environ.get('OVH_CONF', 'ovh.yaml')
ceph_ref      = os.environ.get('CEPH_REF', '')
ceph_repo_url = os.environ.get('CEPH_REPO_URL')

if os.path.isfile(target_file):
    print "Cleanup properties file: [" + target_file + "]"
    os.remove(target_file)

credentials = get_nova_credentials_v2(ovh_conf)

nova_client = Client(**credentials)
print(nova_client.api_version)

target = ''
target_ip = ''
image  = nova_client.images.find(name=target_image)
flavor = nova_client.flavors.find(name=target_flavor)

def create_target():
  srvs = nova_client.servers.list()

  existing_servers = [s.name for s in srvs]
  print range(target_limit)
  for n in range(target_limit):
          target = target_mask % n
          if target in existing_servers:
                  print "Server [" + target + "] already exists."
          else:
                  print "Creating server [" + target + "]"
                  res = nova_client.servers.create(target, image, flavor, key_name=ovh_key)
                  return res
  raise SystemExit('Unable to aquire server resource: Maximum number (' + str(target_limit) + ') of servers reached')



import fcntl

lockfile = '/tmp/mkck'

lock_timeout = 60
lock_wait = 2

res = None

print "Trying to lock file for process " + str(os.getpid())
while True:
        try:
                lock = open(lockfile, 'w')
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                print "File locked for process", os.getpid()
                res = create_target()
                fcntl.flock(lock, fcntl.LOCK_UN)
                print "Unlocking for", str(os.getpid())
                break
        except IOError as err:
                # print "Can't lock: ", err
                if lock_timeout > 0:
                        lock_timeout -= lock_wait
                        print "Process", os.getpid(), "waits", lock_wait, "seconds..."
                        time.sleep(lock_wait)
                else:
                        raise SystemExit('Unable to obtain file lock: %s' % lockfile)

timeout = 8 * 60
wait = 10
target_id = res.id
while res.status != 'ACTIVE':
  #print res, res.name, res.networks, res.status
  if timeout > 0: 
    print 'Server [' + res.name + '] is not active. waiting ' + str(wait) + ' seconds...'
    timeout -= wait
    time.sleep(wait)
  else:
    print "ERROR: Timeout occured, was not possible to make server active"
    break
  res = nova_client.servers.find(id=target_id)

target = res.name
target_ip = res.networks['Ext-Net'][0]
print 'Server [' + target + '] is active and has following IP: ' + target_ip
with open(target_file, 'w') as f:
    f.write('TARGET_NAME=' + target + '\n')
    f.write('TARGET_IP=' + target_ip + '\n')
    f.write('TARGET_IMAGE=' + target_image + '\n')
    f.write('CEPH_REPO_URL=' + ceph_repo_url + '\n')
    f.write('CEPH_REF=' + ceph_ref + '\n')
    f.close()
    print "Saved target properties to file: " + target_file

import paramiko
import logging
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

hostname = target_ip
dependencies = 'git java'
timeout = 300 
wait = 10
home = os.environ.get('HOME')
secret_file = os.environ.get('SECRET_FILE', home + '/.ssh/id_rsa')
print "Connecting to host [" + hostname + "]" 
while True:
        try:
                client.connect(hostname, username='root', key_filename=secret_file)
                print "Connected to the host " + hostname
                break
        except paramiko.ssh_exception.NoValidConnectionsError as e:
                print "Exeption occured: " + str(e)
                if timeout < 0:
                        print "ERROR: Timeout occured"
                        raise e
                else:
                        print "Waiting " + str(wait) + " seconds..."
                        timeout -= wait
                        time.sleep(wait)
target_fqdn = target + ".suse.de"

command_list = [
  'zypper install -y %s 2>&1' % dependencies,
  'echo "' + target_ip + '\t' + target_fqdn + '" >> /etc/hosts',
  'hostname ' + target_fqdn
  ]
if (ceph_ref == 'jewel'):
  command_list.append('zypper remove -y zypper-aptitude 2>&1')

for command in command_list:
  stdin, stdout, stderr = client.exec_command(command)
  while True:
    l = stdout.readline()
    if not l:
      break
    print "> " + l.rstrip()

