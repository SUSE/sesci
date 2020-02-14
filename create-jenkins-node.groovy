// Create jenkins node for the target ovh server
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

Node node = Jenkins.instance.nodes.find { it.nodeName == nodeName }
if (node) {
    print 'Node "' + nodeName + '" exists. Disconnect at first... '
    def c = node.toComputer()
    c.disconnect()
    def timeout = 5 * 60
    def wait = 10
    while (c.online) {
        println "Node [" + node.nodeName + "] is online. Waiting " + wait + " seconds"
        if (timeout > 0) {
            timeout -=  wait
        } else {
            println "ERROR: Can't make the node offline"
        }
        sleep(wait * 1000)
    }
    println "DONE"
    print "Removing node... "
    Jenkins.instance.removeNode(node)
    println "DONE"
}

node = new DumbSlave(nodeName, nodeName + ' [auto]', '/opt/j', '1', Node.Mode.NORMAL, 'make-check',
        new SSHLauncher(nodeHost, 22, credName ), new RetentionStrategy.Always(), new LinkedList() )
Jenkins.instance.addNode(node)
println 'Created node "' + nodeName + '". Connecting...'

def c = node.computer
c.connect(true)
def timeout = 3 * 60
def wait = 10
while (c.offline) {
    if (timeout > 0) {
        timeout -=  wait
    } else {
        println "ERROR: Timeout. Can't get the node online"
        return -1
    }
    println "Node [" + node.nodeName + "] is offline. Waiting " + wait + " seconds"
    sleep(wait * 1000)
}


