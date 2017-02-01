import hudson.model.*

def env = binding.variables

// println env

def suse_ver = env['SUSE_VER']
def ceph_ver = env.get('CEPH_VER', 'suse')
def flavor   = env.get('TARGET_FLAVOR', 'hg-15-ssd')

def ceph_map = [
  'ceph':  ['ceph/ceph', 'master'],
  'suse':  ['suse/ceph', 'master'],
  'ses3':  ['suse/ceph', 'ses3'],
  'ses4':  ['suse/ceph', 'ses4'],
  'ses5':  ['suse/ceph', 'ses5'],
  'jewel': ['ceph/ceph', 'jewel']
  ]


def suse_image_map = [
  'leap-42.2': 'teuthology-opensuse-42.2-x86_64',
  'sle12-sp1': 'teuthology-sle-12.1-x86_64',
  'sle12-sp2': 'teuthology-sle-12.2-x86_64'
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
    numToKeep (5)
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
      file('OVH_CONF', 'ovh-conf')
      file('SECRET_FILE', 'sa')
    }
  }
  steps {
    shell ('git clone https://github.com/kshtsk/sesci .')
	shell ('python create-ovh-server.py')
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
    systemGroovyCommand(readFileFromWorkspace('delete-jenkins-node.groovy'))
	shell ('python delete-ovh-server.py')
    copyArtifacts(mkck) {
      includePatterns('build/**', 'src/**/*.log', 'src/**/*.trs')
      optional()
      buildSelector {
        multiJobBuild()
      }
    }
    if (ceph_branch == "ses4" || ceph_branch == "jewel") {
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
    }

}

job(mkck) {
  customWorkspace('ws/mkck')
  concurrentBuild()
  logRotator {
    numToKeep (5)
  }
  wrappers {
    preBuildCleanup()
    timeout {
      // absolute(200) // 3:20 hrs
      absolute(150) //  2:30 hrs
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
    if (['ses4', 'jewel'].contains(ceph_branch)) {
      if (['leap-42.2'].contains(suse_ver) {
        cmds.add("ulimit -u 10240")
      }
      cmds.add("""./run-make-check.sh""")
    }
    else {
      cmds.add("""./run-make-check.sh -DWITH_LTTNG=false""")
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

