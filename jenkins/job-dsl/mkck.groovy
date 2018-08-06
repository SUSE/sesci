import hudson.model.*

def env = binding.variables

// println env

def suse_ver = env['SUSE_VER']
def ceph_ver = env.get('CEPH_VER', 'suse')
//def flavor   = env.get('TARGET_FLAVOR', 'hg-15-ssd')
//def flavor   = env.get('TARGET_FLAVOR', 'c2-15')
def flavor   = env.get('TARGET_FLAVOR', 'b2-30')

// https://www.ovh.com/world/public-cloud/instances/prices/
//
//
//	Model	RAM	Processor	Freq.	Storage		Bandwidth		Price/hour
//		GB	vCores			Local SSD RAID	pub. guranteed/
//								max. vRack
//
// GENERAL PURPOSE Instances - Guaranteed resources, a balance of CPU/RAM
//	B2-7	7 GB	2 vCores	2.3 GHz	50 GB		250 Mbps/300 Mbps	$0.074
//	B2-15	15 GB	4 vCores	2.3 GHz	100 GB		250 Mbps/1000 Mbps	$0.140
//	B2-30	30 GB	8 vCores	2.3 GHz	200 GB		500 Mbps/2000 Mbps	$0.284
//	B2-60	60 GB	16 vCores	2.3 GHz	400 GB		500 Mbps/4000 Mbps	$0.551
//	B2-120	120 GB	32 vCores	2.3 GHz	400 GB		500 Mbps/4000 Mbps	$1.084
//
// CPU Instances - Guaranteed resources, very high frequency CPU
//	C2-7	7 GB	2 vCores	3.1 GHz	50 GB		250 Mbps/300 Mbps	$0.107
//	C2-15	15 GB	4 vCores	3.1 GHz	100 GB		250 Mbps/1000 Mbps	$0.207
//	C2-30	30 GB	8 vCores	3.1 GHz	200 GB		500 Mbps/2000 Mbps	$0.417
//	C2-60	60 GB	16 vCores	3.1 GHz	400 GB		500 Mbps/4000 Mbps	$0.817
//	C2-120	120 GB	32 vCores	3.1 GHz	400 GB		500 Mbps/4000 Mbps	$1.617
//
// RAM Instances - Guaranteed resources, optimized RAM/cost ratio
//	R2-15	15 GB	2 vCores	2.4 GHz	50 GB		250 Mbps/1000 Mbps	$0.107
//	R2-30	30 GB	2 vCores	2.4 GHz	50 GB		250 Mbps/1000 Mbps	$0.124
//	R2-60	60 GB	4 vCores	2.4 GHz	100 GB		250 Mbps/2000 Mbps	$0.240
//	R2-120	120 GB	8 vCores	2.4 GHz	200 GB		500 Mbps/4000 Mbps	$0.484
//	R2-240	240 GB	16 vCores	2.4 GHz	400 GB		500 Mbps/4000 Mbps	$0.950

//	Model	RAM	Processor	Frequency	Storage, SSD	Bandwidth	Price/hour
//		GB	vCores		BEST EFFORT	Local RAID 10	BEST EFFORT
//
// SANDBOX Instances - Shared resources
// 	S1-2	2 GB	1 vCore		2.4 GHz		10 GB		100 Mbps public	$0.009/hour
//	S1-4	4 GB	1 vCore		2.4 GHz		20 GB		100 Mbps public	$0.024/hour
//	S1-8	8 GB	2 vCores	2.4 GHz		40 GB		100 Mbps public	$0.044/hour

// https://www.ovh.com/world/public-cloud/instances/prices/old.xml
//
// HG Instances
//	Model	RAM	Processor	Freq.	Storage		Bandwidth		Price/hour
//						HA or		public guranteed or
//						SSD No RAID	max. vRack
//
//	HG-7	7 GB	2 vCores	3.1 GHz	200 GB/100 GB	250 Mbps/300 Mbps	$0.107
//	HG-15	15 GB	4 vCores	3.1 GHz	400 GB/200 GB	250 Mbps/1000 Mbps	$0.207
//	HG-30	30 GB	8 vCores	3.1 GHz	800 GB/400 GB	500 Mbps/2000 Mbps	$0.417
//	HG-60	60 GB	16 vCores	3.1 GHz	1600 GB/800 GB	500 Mbps/4000 Mbps	$0.817
//	HG-120	120 GB	32 vCores	3.1 GHz	1600 GB/800 GB	500 Mbps/4000 Mbps	$1.617
//
//	EG-7	7 GB	2 vCores	2.3 GHz	200 GB/100 GB	250 Mbps/300 Mbps	$0.074
//	EG-15	15 GB	4 vCores	2.3 GHz	400 GB/200 GB	250 Mbps/1000 Mbps	$0.140
//	EG-30	30 GB	8 vCores	2.3 GHz	800 GB/400 GB	500 Mbps/2000 Mbps	$0.284
//	EG-60	60 GB	16 vCores	2.3 GHz	1600 GB/800 GB	500 Mbps/4000 Mbps	$0.551
//	EG-120	120 GB	32 vCores	2.3 GHz	1600 GB/800 GB	500 Mbps/4000 Mbps	$1.084
//
// VPS-SSD Instances
//	Model		RAM	Processor	Frequency	Storage		Bandwidth	Price/hour
//						BEST EFFORT	Local RAID 10	BEST EFFORT
//
//	VPS-SSD 1	2 GB	1 vCore		2.4 GHz		10 GB SSD	100 Mbps public	$0.009/hour
//	VPS-SSD 2	4 GB	1 vCore		2.4 GHz		20 GB SSD	100 Mbps public	$0.024/hour
//	VPS-SSD 3	8 GB	2 vCores	2.4 GHz		40 GB SSD	100 Mbps public $0.044/hour

def ceph_map = [
  'ceph':  ['ceph/ceph', 'master'],
  'suse':  ['suse/ceph', 'master'],
  'ses2':  ['suse/ceph', 'ses2'],
  'ses3':  ['suse/ceph', 'ses3'],
  'ses4':  ['suse/ceph', 'ses4'],
  'ses5':  ['suse/ceph', 'ses5'],
  'ses6':  ['suse/ceph', 'ses6'],
  'jewel': ['ceph/ceph', 'jewel'],
  'luminous':  ['ceph/ceph', 'luminous']
  ]


def suse_image_map = [
  'leap-42.1': 'makecheck-opensuse-42.1-x86_64',
  'leap-42.2': 'makecheck-opensuse-42.2-x86_64',
  'leap-42.3': 'makecheck-opensuse-42.3-x86_64',
  'leap-15.0': 'makecheck-opensuse-15.0-x86_64',
  'sle15':     'makecheck-sle-15.0-x86_64',
  'sle12-sp1': 'makecheck-sle-12.1-x86_64',
  'sle12-sp2': 'makecheck-sle-12.2-x86_64',
  'sle12-sp3': 'makecheck-sle-12.3-x86_64'
  ]

def ceph_repo_url = env.get('ghprbAuthorRepoGitUrl', 
  "https://github.com/" + ceph_map[ceph_ver][0] + ".git")
def ceph_branch   = env.get('ghprbTargetBranch', ceph_map[ceph_ver][1])

def ceph_ref      = env['CEPH_REF']
if (ceph_ref == null || ceph_ref == '') {
  ceph_ref        = ceph_branch
}

def suse_image    = suse_image_map[suse_ver]

def mkck = "run-mkck-${ceph_ver}-${suse_ver}"

multiJob("mkck-${ceph_ver}-${suse_ver}") {
  label('master')
  logRotator {
    numToKeep (9)
  }

  configure { project ->
    project / 'properties' / 'hudson.security.AuthorizationMatrixProperty' {
      permission('hudson.model.Item.Read:anonymous')
      permission('hudson.model.Item.ViewStatus:anonymous')
    }
  }
  concurrentBuild()
  parameters {
    booleanParam('DESTROY_ENVIRONMENT', true)
    stringParam('SUSE_VER', '', 'For example:<ul><li>leap42.2<li>sle12.2<li>sle12.1</ul>')
    stringParam('CEPH_REF', ceph_ref, '')
    stringParam('CEPH_VER', '', 'For example:<ul><li>ceph<li>suse<li>ses5<li>ses4<li>ses3</ul>')
    stringParam('TARGET_FILE', 'mkck.properties', 'Target properties')
    stringParam('TARGET_FLAVOR', flavor)
    stringParam('TARGET_IMAGE', suse_image)
    stringParam('CEPH_REPO_URL', ceph_repo_url)
  }
  wrappers {
    preBuildCleanup()
    credentialsBinding {
      file('OVH_CONF', 'storage-os-conf')
      file('SECRET_FILE', 'storage-automation-secret-file')
    }
  }
  steps {
    shell ('git clone https://github.com/suse/sesci .')
    shell ('python -u create-ovh-server.py')
    shell ('cat ${TARGET_FILE}')
    environmentVariables {
      propertiesFile('${TARGET_FILE}')
    }
    systemGroovyCommand(readFileFromWorkspace('create-jenkins-node.groovy'))
    phase('Ceph run-make-check') {
      continuationCondition('ALWAYS')
      phaseJob(mkck) {
        abortAllJobs(true)
        currentJobParameters(true)
        parameters {
          propertiesFile('${TARGET_FILE}')
        }
      }
    }
    shell ('ssh -i ${SECRET_FILE} -o StrictHostKeyChecking=no root@${TARGET_IP} coredumpctl || true')
    shell ('scp -r -i ${SECRET_FILE} -o StrictHostKeyChecking=no root@${TARGET_IP}:/var/lib/systemd/coredump . || true')
    systemGroovyCommand(readFileFromWorkspace('delete-jenkins-node.groovy'))
	shell ('python -u delete-ovh-server.py')
    copyArtifacts(mkck) {
      includePatterns('build/**', 'src/**/*.log', 'src/**/*.trs')
      optional()
      buildSelector {
        multiJobBuild()
      }
    }
    if (['ses2', 'ses3', 'ses4', 'jewel'].contains(ceph_branch)) {
        shell ('python convert-trs-to-junit.py src res')
    } else {
        shell ('python convert-ctest-to-junit.py')
    }
  }
  publishers {
        archiveJunit('res/make-check.xml') {
            allowEmptyResults()
            testDataPublishers {
                publishTestAttachments()
            }
        }
        archiveArtifacts {
          pattern('coredump/**')
          allowEmpty()
        }
    }

}

job(mkck) {
  customWorkspace('ws/mkck')
  concurrentBuild()
  logRotator {
    numToKeep (9)
  }
  wrappers {
    preBuildCleanup()
    timeout {
      // absolute(200) // 3:20 hrs
      absolute(180) //  3:00 hrs
      // absolute(150) //  2:30 hrs
      // absolute(120) //  2:00 hrs
      // absolute(100) //  1:40 hrs
    }
  }
  parameters {
    stringParam('CEPH_REPO_URL')
    stringParam('CEPH_REF')
    stringParam('TARGET_NAME')    
  }
  configure { project ->
    project / 'properties' / 'jp.ikedam.jenkins.plugins.groovy__label__assignment.GroovyLabelAssignmentProperty' {
      'secureGroovyScript' {
        script ('binding.getVariables().get("TARGET_NAME")')
      }
    }
    project / 'properties' / 'hudson.security.AuthorizationMatrixProperty' {
      permission('hudson.model.Item.Read:anonymous')
      permission('hudson.model.Item.ViewStatus:anonymous')
    }

  }
  scm {
    git {
      remote {
        url ('$CEPH_REPO_URL')
      }
      branch('$CEPH_REF')
    }
  }

  def cmds = [
    """echo \$(hostname -i) \$(hostname -f)""",
    """cat /etc/os-release"""
  ]
  steps {
    if (['ses2', 'ses3', 'ses4', 'jewel'].contains(ceph_branch)) {
      if (['leap-42.1', 'leap-42.2', 'leap-42.3'].contains(suse_ver)) {
        cmds.add("ulimit -u 10240")
      }
      cmds.add("""./run-make-check.sh""")
    }
    else if(['ses5'].contains(ceph_branch)) {
      cmds.add("""./run-make-check.sh -DWITH_LTTNG=false -DWITH_BABELTRACE=false""")
    }
    else {
      cmds.add("""./run-make-check.sh -DWITH_LTTNG=false -DWITH_BABELTRACE=false""")
    }
    shell(cmds.join("\n"))
  }
  publishers {
    archiveArtifacts {
      pattern('build/Testing/**')
      pattern('src/**/*.trs')
      pattern('src/**/*.log')
      pattern('test-suite.log')
      allowEmpty()
    }
  }
}

