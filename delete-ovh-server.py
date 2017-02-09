# Remove OVH server
import os
import yaml
import time

def get_nova_credentials_v2():
    d = {}
    ovh_conf = os.environ.get('OVH_CONF', 'ovh.yaml')
    with open(ovh_conf) as y:
        c = yaml.load(y)
        d['username']    = c.get('OS_USERNAME')
        d['api_key']     = c.get('OS_PASSWORD')
        d['auth_url']    = c.get('OS_AUTH_URL')
        d['project_id']  = c.get('OS_TENANT_NAME')
        d['region_name'] = c.get('OS_REGION_NAME')
    d['version'] = '2'
    return d


from novaclient.client import Client

destroy_env   = os.environ.get('DESTROY_ENVIRONMENT')
target_name   = os.environ.get('TARGET_NAME')

if (destroy_env == 'true') :
  credentials = get_nova_credentials_v2()
  
  nova_client = Client(**credentials)
  print(nova_client.api_version)
  
  print "Looking for server [" + target_name + "]"
  t = nova_client.servers.find(name=target_name)
  if t:
    print "Removing server [" + t.name + "]"
    t.delete()
else:
  print "Leaving server [" + target_name + "] alone..."
