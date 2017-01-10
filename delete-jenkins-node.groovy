// Delete jenkins node 
print "Delete jenkins node"

import jenkins.model.Jenkins
import hudson.model.Node

import hudson.slaves.DumbSlave
import hudson.plugins.sshslaves.SSHLauncher
import hudson.slaves.RetentionStrategy

def env = [:]
env = build.getEnvironment(listener)

def credName = 'storage-automation'
def nodeName = env.get('TARGET_NAME', 'undefined')
def nodeHost = env.get('TARGET_IP', 'undefined')
def destroy  = env.get('DESTROY_ENVIRONMENT')

if (destroy != 'true') {
    print "Skipping jenkins node cleanup as requested DESTROY_ENVIRONMENT"
	return 0
}
Node node = Jenkins.instance.nodes.find { it.nodeName == nodeName }
if (node) {
    print 'Node "' + nodeName + '" exists. Disconnect at first... '
    def c = node.toComputer()
    c.disconnect()
    def timeout = 10 * 60
    def wait = 10
    while (c.online) {
        println "Node [" + node.nodeName + "] is online. Waiting " + wait + " seconds"
        if (timeout > 0) {
            timeout -=  wait
        } else {
            println "ERROR: Can't make the node offline"
            return 0
        }
        sleep(wait * 1000)
    }
    println "DONE"
    print "Removing node... "
    Jenkins.instance.removeNode(node)
    println "DONE"
}

