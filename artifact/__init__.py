"""Tool for artifact delivery


This tool takes artifact description file as an input
determines location for each of artifacts, uploads to
a destination server provided in the config file and
returns artifacts dictionary with URLs by which every
artifacts can be accessed.


Artifacts:

Artifact description file contents example `description.yaml`:


    - name: 'ses!2'
      id: Devel-Storage-6-Media1
      delivery: rsync
      url: /mnt/dist/ibs/Devel:/Storage:/6.0/images/repo/
      filters: POOL-x86_64 Media1$
    - name: 'internal!2'
      id: Devel-Storage-6-Internal-Media
      delivery: rsync
      url: /mnt/dist/ibs/Devel:/Storage:/6.0/images/repo/
      filters: POOL-Internal-x86_64 Media$

Artifacts results:

    artifacts:
      internal!2:
        src: /mnt/dist/ibs/Devel:/Storage:/6.0/images/repo/SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Media
        url: http://localhost/artifacts/ci/55aa42e88aed8a21fbeb4c97c36420d7f249850f7ee40a270e7d83f275d94bdc/SUSE-Enterprise-Storage-6-POOL-Internal-x86_64-Build14.36
      ses!2:
        src: /mnt/dist/ibs/Devel:/Storage:/6.0/images/repo/SUSE-Enterprise-Storage-6-POOL-x86_64-Media1
        url: http://localhost/artifacts/ci/6b05772d5e311954b2cbe3a3c296818d75e628ea0ec7b4591e83e4073bd58d71/SUSE-Enterprise-Storage-6-POOL-x86_64-Build14.51


Delivery config contents example `delivery.conf`:

    mirror:
        delivery_address: 'scp://localhost:/tmp/ci/artifacts'
        access_address: 'http://localhost/artifacts'
    snapshot:
        delivery_address: 'snap://localhost:/tmp/ci/artifacts'
        access_address: 'http://localhost/artifacts'
    rsync:
        delivery_address: 'rsync:/localhost:/tmp/ci/artifacts'
        access_address:   'http://localhost/artifacts'

Note: For the example above there should be sshd service up and running
on the localhost, as well as http server providing access to the `/tmp/ci`,
for instance, it can be done with `http.server` python3 module:

    (mkdir -p /tmp/ci ; cd /tmp/ci ; python3 -m http.server 80)

For satisfying requirements install corresponding dependencies
using system package manager or pip:

    lxml lxml pyyaml requests

Usage:

    python3 -um artifact determine -i <yaml> -D <conf> -o <artifacts>
    python3 -um artifact deliver -i <yaml> -D <conf> -o <artifacts>

"""

import argparse
import fcntl
import hashlib
import logging
import lxml.html
import os
import pprint
import re
import requests
import sys
import time
import yaml
import json

class Delivery():
    """
        Delivery class 
    """
    delivery_address = "scp://ci.suse.de@storage-ci.suse.de:/mnt/shared/artifacts"
    access_address = "http://storage-ci.suse.de/artifacts"
    def __init__(self, m_addr, a_addr):
        delivery_address = m_addr
        access_address = a_addr
    @staticmethod
    def read_conf(filename):
        """
            Config file has yaml format.
            And represent a map:
            <delivery-name>
                delivery_address: 'url'
                access_address: 'url'
        """
        with open(filename, 'r') as f:
            conf = yaml.load(f)




class Artifact():
    workdir = '/tmp/artifacts'
    name = ""
    #type = "mirror"
    a_ref = ""
    s_ref = ""
    d_ref = ""
    _id = ""
    @staticmethod
    # resolve build id
    def resolve_id(repo_url):
        if repo_url.endswith('.iso'):
            return Artifact.fname(repo_url)
        else:
            urls = [
                repo_url.rstrip('/') + '/media.1/build',
                repo_url.rstrip('/') + '/media.1/media' 
            ]
            for url, u in [(x, Artifact.parse_url(x)) for x in urls]:
                if u['proto'] == 'file':
                    if (os.path.isfile(u['path'])):
                        with open(u['path'], 'r') as f:
                            data = str(f.read())
                    else:
                        continue
                if u['proto'] == 'http' or u['proto'] == 'https':
                    r = requests.get(u['url'])
                    if r.status_code != 200:
                        logging.info("URL %s failed with status: %s" % (u['url'], r.status_code))
                        continue
                    else:
                        data = str(r.text)
                        logging.info(data)
                if (u['path'].endswith('build')):
                    return data.strip()
                if (url.endswith('media')):
                    return data.split('\n')[1].strip()
            logging.warning("URL %s was not able to detect an id" % repo_url)
            return Artifact.fname(repo_url.rstrip('/'))

    def __init__(self, name, source, delivery = None, aid = None, exclude = None):
        """
           delivery
                delivery_address: 
                access_address:
        """
        self.name = name
        self.s_ref = source
        self.delivery = delivery
        self.aid = aid
        self.exclude = exclude

        if (delivery):
            self.delivery_address = delivery['delivery_address']
            self.access_address = delivery['access_address']
            resolved_id = Artifact.resolve_id(self.s_ref)
            logging.info("Resolved id is: '" + resolved_id + "'")
            self._id = self.aid or resolved_id
            logging.info("Artifact id is: '" + self._id + "'")
            self.d_ref = self.delivery_address.rstrip('/') + \
                '/' + self.id() + '/' + self._id
            self.a_ref = self.access_address.rstrip('/') + \
                '/' + self.id() + '/' + self._id
            u = self.parse_url(self.delivery_address)
            if u['proto'] == 'rsync':
                self.r_ref = self.delivery_address.rstrip('/') + \
                    '/' + self.id() + '/' + self._id + '.rsync'
                self.d_ref = self.delivery_address.rstrip('/') + \
                    '/' + self.id() + '/' + resolved_id
                self.a_ref = self.access_address.rstrip('/') + \
                    '/' + self.id() + '/' + resolved_id
            if u['proto'] == 'snap':
                d_tag = time.strftime('%Y%m%d%H%M')
                self.r_ref = self.delivery_address.rstrip('/') + \
                    '/' + self.id() + '/' + self._id + '.rsync'
                self.d_snap = u['path'].rstrip('/') + \
                    '/snapshot/' + d_tag + '/' + self.id() + '/' + self._id
                self.a_ref = self.access_address.rstrip('/') + \
                    '/snapshot/' + d_tag + '/' + self.id() + '/' + self._id
        else:
            self.a_ref = self.s_ref
    @staticmethod
    def fname(path):
        return path.rstrip('/')[path.rstrip('/').rfind('/')+1:]
    delivery = None
    cache_dir = "/tmp/artifacts-cache"
    def id(self):
        return self.artifact_id()
    def artifact_id(self):
        # We need to prepend source reference because different project on obs
        # can have same build id.
        a = (self.aid or self.s_ref) + ':' + self._id
        return hashlib.sha256(a.encode('ascii')).hexdigest()
    def cache_file(self):
        ref = self.s_ref.rstrip('/')
        return self.cache_dir + '/' + self.artifact_id() + '/' + ref[ref.rfind('/')+1:]
    @staticmethod
    def parse_url(url):
        url_re = re.compile("(?:([a-zA-Z]+)://)?((?:([a-zA-Z0-9_\.-]+)@)?([0-9a-zA-Z_\.-]+)(?::([0-9]+))?)?:?(/.*)$")
        m = url_re.match(url)
        res = {
            'proto': m.group(1) or 'file',
            'addr': m.group(2),
            'user': m.group(3),
            'host': m.group(4),
            'port': m.group(5),
            'path': m.group(6),
            'url': url
        }
        return res
        
    def delivered(self):
        '''check existence presence file by d_ref'''
        host = self.parse_url(self.d_ref)
        if host['proto'] == 'snap':
            logging.info("Checking snapshot for presence at host %s" % host['addr'])
            return os.system("ssh -q %s stat %s 1>/dev/stderr" % (host['addr'], self.d_snap)) == 0
        logging.info("Checking presence of artifact [%s] on the host [%s]" % (Artifact.fname(host['path']), host['host']))
        return os.system("ssh -q %s stat %s 1>/dev/stderr" % (host['addr'], host['path'])) == 0
    def __repr__(self):
        return yaml.dump({
        self.name: {
            'source': self.s_ref,
            'access': self.a_ref,
            'cache': self.cache_file()
        }},default_flow_style=False, default_style="")
    def _download(self):
        # add check if there partly downloaded already
        url = self.parse_url(self.s_ref)
        if url['proto'] == 'file':
            logging.debug('Do not download artifacts if proto is file.')
            return
        d = os.path.dirname(self.cache_file())
        if not os.path.exists(d):
            os.makedirs(d) 
        if (self.s_ref.endswith('.iso')):
            res = os.system("wget -c -O %s %s" % (self.cache_file(), self.s_ref))
            if res != 0:
                raise Exception('Download failed')
        else:
            a_dir = self.cache_dir + '/' + self.artifact_id() + '/mirror'
            log   = self.cache_dir + '/' + self.artifact_id() + '/log'
            mirror = "wget -m -nH -np -R mirrorlist,metalink,meta4,index.html* -P %s -o %s %s" % (a_dir, log, self.s_ref.rstrip('/')+'/')
            logging.info("Mirroring %s" % self.s_ref)
            logging.info("> %s" % mirror)
            res = os.system(mirror)
            if res != 0 and res/256 != 8:
                raise Exception('Download failed with exit code %d' % res)
            url = self.parse_url(self.s_ref.rstrip('/'))
            res = os.system("mv %s %s" %(self.cache_file(), self.cache_file() + time.strftime(".%Y%m%d-%H%M%S", time.gmtime())))
            res = os.system("mv %s %s" %(a_dir + '/' + url['path'], self.cache_file()))
            res = os.system("rm -rf %s" %(a_dir))
 
    def _mirror(self):
        s_url = self.parse_url(self.s_ref)
        s_file = self.cache_file()
        if s_url['proto'] == 'file':
            s_file = s_url['path']
        url = self.parse_url(self.d_ref)
        temp = url['path'] + '.part'
        orig = url['path']
        logging.info("Mirroring artifact [%s] to [%s] using [%s]" % \
                (self.name, url['addr'], url['proto']))
        if url['proto'] == 'scp':
            fdir = os.path.dirname(url['path'])
            if fdir != "" and fdir != "/":
                logging.debug("Making path: %s" % fdir)
                os.system('ssh -q %s mkdir -p %s' % (url['addr'], fdir))
                os.system('ssh -q %s rm -rf %s' % (url['addr'], temp))
            if os.system('scp -r %s %s' % (s_file, url['addr']+ ":" + temp)) == 0:
                os.system('ssh -q %s mv %s %s' % (url['addr'], temp, orig))
                if s_url['proto'] != 'file':
                    os.system('rm -rf %s' % (s_file))
                # unpack iso image
                if orig.endswith('.iso'):
                    logging.info("ISO image detected, unpacking it")
                    udir = orig[:-len('.iso')]
                    os.system('ssh -q %s mkdir -p %s' % (url['addr'], udir))
                    os.system('ssh -q %s "cd %s ; 7z x %s"' % (url['addr'], udir, orig))
                    # fix 7z iso unpacking directories permission issue
                    os.system('ssh -q %s "chmod -R a+rX %s"' % (url['addr'], udir))
        elif url['proto'] == 'rsync':
            r_url = self.parse_url(self.r_ref)
            r_dir = r_url['path']
            d_dir = os.path.dirname(r_dir)
            logging.info('Syncing dir %s to %s' % (s_file, r_dir))
            res = os.system('rsync -avz --delete '
                '--rsync-path "mkdir -p %s && rsync" %s/ %s' % \
                    (d_dir, s_file, url['addr'] + ":"+ r_dir))
            if res:
                raise Exception('Syncing failed due to rsync exit code: %s' % res)
            logging.info('Moving remote dir %s to %s' % (r_dir, orig))
            os.system('ssh -q %s cp -r %s %s' % (url['addr'], r_dir, orig))
        elif url['proto'] == 'snap':
            r_url = self.parse_url(self.r_ref)
            r_dir = r_url['path']
            d_dir = os.path.dirname(r_dir)
            logging.debug('Syncing dir %s to %s' % (s_file, r_dir))
            #exclude_list = self.exclude or ['aarch64*/', 's390*/', 'ppc64*/', 'src/', 'i586/', 'i686/']
            exclude_list = self.exclude
            excludes = ''
            if exclude_list:
                excludes = "".join(f'--exclude "{i}" ' for i in exclude_list)
            dest = url['addr'] + ':' + r_dir
            cmd = f'rsync -avz --delete {excludes} ' + \
                  f'--rsync-path "mkdir -p {d_dir} && rsync" ' + \
                  f'{s_file}/ {dest} 1>/dev/stderr'
            logging.debug(f'Using command: {cmd}')
            res = os.system(cmd)
            if res:
                raise Exception('Snapshotting failed due to rsync exit code: %s' % res)
            logging.info('Snapshot to %s' % self.d_snap)
            cmd = "mkdir -p {dst_parent} ; cp -r {src_dir} {dst_dir}".format(
                    src_dir=r_dir,
                    dst_dir=self.d_snap,
                    dst_parent=os.path.dirname(self.d_snap),
                )
            logging.debug("Remote run: %s" % cmd)
            os.system('ssh -q %s "%s"' % (url['addr'], cmd))


    def _deliver(self):
        if self.d_ref:
            if self.delivered():
                logging.info("Aritfact '%s' is already delivered", self.name + ':' + self._id)
            else:
                self._download()
                self._mirror()
        else:
            logging.warning("Artifact is not deliverable")
    @staticmethod
    def from_desc(desc, delivery_map=None):
        url = Artifact.resolve_url(desc['url'], desc['filters'].split(' '))
        d = desc['delivery']
        logging.info("Using delivery '%s'", d)
        if d not in delivery_map:
            logging.warning('Cannot find delivery "%s" in delivery map', d)
        delivery = delivery_map[d] if (d != 'direct' and 
            delivery_map and d in delivery_map.keys()) \
                 else None
        return Artifact(desc['name'], url, delivery,
                        aid=desc.get('id', None),
                        exclude=desc.get('exclude', None))
        
    @staticmethod
    def resolve_url(url, filters):
        """
        Returns first subdirectory for base url matched each of the given filters,
        similar to grep. Returns None if no matching url found.
        """
        u = Artifact.parse_url(url)
        if u['proto'] == 'file':
            # it is a file path
            if (os.path.isdir(u['path'])):
                logging.info('Reading dir %s' % u['path'])
                urls = os.listdir(u['path'])
            else:
                logging.error("There is no directory by path %s" % u['path'])
                return None
        else:
            r = requests.get(url)
            if r.status_code != 200:
                logging.error("URL %s failed with status: %s" % (url, r.status_code) )
                return None
            doc = lxml.html.fromstring(r.text)
            urls = doc.xpath('//a/@href')
        patterns = [re.compile(".*%s" %f) for f in filters] 
        filtered = [ url.rstrip('/') + '/' + x for x in set(urls)
                            if all([r.match(x.rstrip('/')) for r in patterns]) ]
        ref = filtered[0] if len(filtered) > 0 else None
        if ref == None:
            logging.warn("URL %s with filters [%s] do not give any result" % (url, ", ".join(filters)))
        return ref
        
    def deliver(self):
        if not self.d_ref:
            logging.error("Artifact %s is not deliverable" % self)
            return
        lock_timeout_secs = 90*60
        lock_wait_secs = 2*60

        lockfile = self.workdir + '/' + self.artifact_id()
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir) 
        logging.debug("Trying to lock artifact [%s]" % (lockfile))
        start = time.time()
        while True:
            try:
                lock = open(lockfile, 'w')
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                logging.debug("Artifact locked for process %s" % os.getpid())
                res = self._deliver()
                fcntl.flock(lock, fcntl.LOCK_UN)
                logging.debug("Unlocking for %s" % str(os.getpid()))
                break
            except IOError as err:
                #   [Errno 35] Resource temporarily unavailable
                if "Resource temporarily unavailable" in str(err):
                    logging.info("Artifact is already locked by other process")
                else:
                    logging.error("Can't lock artifact: %s", err)
                if time.time() - start < lock_timeout_secs:
                    logging.debug(
                        "Process {p} must wait {w} seconds "
                        "to give another try to lock file '{f}'"
                        .format(p=os.getpid(), w=lock_wait_secs, f=lockfile))
                    logging.info("Waiting %s seconds..." % lock_wait_secs)
                    time.sleep(lock_wait_secs)
                else:
                    raise SystemExit('Unable to obtain file lock: %s' % lockfile)


def determine_with_desc(desc_file, delivery_conf=None):
    delivery = None
    if delivery_conf:
        with open(delivery_conf, 'r') as f:
            delivery = yaml.safe_load(f)
    desc = yaml.safe_load(desc_file)
    artifacts=[Artifact.from_desc(d, delivery) for d in desc]
    return artifacts

def deliver_with_desc(desc_file, delivery_conf=None):
    artifacts=determine_with_desc(desc_file, delivery_conf)
    for a in artifacts:
        a.deliver()
    return artifacts

def dump_artifacts(artifacts, fmt='yaml'):
    if fmt == 'yaml':
        return yaml.dump({'artifacts': {
            a.name: {
                'src': a.s_ref,
                'url': a.a_ref
            } for a in artifacts}},
                default_flow_style=False,
                default_style="")
    elif fmt == 'json':
        return json.dumps({'artifacts': {
            a.name: {
                'src': a.s_ref,
                'url': a.a_ref
            } for a in artifacts}}, indent=4)
    elif fmt == 'zypper':
        repos = []
        for a in artifacts:
            n = a.name.split('!', 1)
            r = dict(
                name=n[0],
                zypper=dict(
                    baseurl=a.a_ref,
                    enabled=1,
                )
            )
            if len(n) > 1:
                r['zypper']['priority'] = int(n[1])
            repos += [r]
        return '\n'.join(
                "[%s]\n" % r['name'] + ('\n'.join('%s=%s' % (k, v) for k,v in r['zypper'].items()))
                    for r in repos)
    elif fmt == 'yaml-list':
        repos = []
        for a in artifacts:
            n = a.name.split('!', 1)
            r = dict(
                name=n[0],
                url=a.a_ref,
            )
            if len(n) > 1:
                r['priority'] = int(n[1])
            repos += [r]
        return yaml.safe_dump(repos,
                default_flow_style=False,
                default_style="")
    elif fmt == 'json-list':
        repos = []
        for a in artifacts:
            n = a.name.split('!', 1)
            r = dict(
                name=n[0],
                url=a.a_ref,
            )
            if len(n) > 1:
                r['priority'] = int(n[1])
            repos += [r]
        return json.dumps(repos, indent=4)


def main():
    parser = argparse.ArgumentParser(description='Artifact delivery tool')
    parser.add_argument('action',
                    help='Action', choices=['deliver', 'determine'])
    parser.add_argument('-i', '--input', default=sys.stdin, type=argparse.FileType('r'),
        help='Artifacts description file')
    parser.add_argument('-o', '--output', default=sys.stdout, type=argparse.FileType('w'),
        help='Save determined artifacts to file')
    parser.add_argument('-D', '--delivery', default=os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + '/.')
            + '/delivery.conf',
        help='Delivery configuration')
    parser.add_argument('-f', '--format', default='yaml',
        choices=['yaml', 'json', 'zypper', 'zypper-addrepo', 'yaml-list', 'json-list'],
        help='Output format')
    parser.add_argument('-v', '--verbose', default=False, action='store_true',
        help='Be more verbose')
    parser.add_argument('-d', '--debug', default=False, action='store_true',
        help='Be more verbose')
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')
    elif args.verbose:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(message)s')
    else:
        logging.basicConfig(level=logging.WARNING, format='%(levelname)s:%(message)s')
    action = args.action
    desc_file = args.input
    delivery_conf = args.delivery
    if (action == 'deliver'):
        artifacts = deliver_with_desc(desc_file, delivery_conf)
        args.output.write(dump_artifacts(artifacts, args.format))
    elif (action == 'determine'):
        artifacts = determine_with_desc(desc_file, delivery_conf)
        args.output.write(dump_artifacts(artifacts, args.format))
    else:
        logging.error("Unknown action %s" % action)

