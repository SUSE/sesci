import os
import yaml
import sys

from xml.etree.ElementTree import Element, SubElement, Comment, tostring

TargetPath = "src"
if (len(sys.argv) > 1):
        TargetPath = sys.argv[1]

OutputDirPath = None
if (len(sys.argv) > 2):
        OutputDirPath = sys.argv[2]
	try:
        	os.stat(OutputDirPath)
	except:
        	os.mkdir(OutputDirPath)

try:
        os.stat(TargetPath)
except:
        print "Log file [" + TargetPath + "] does not exists. Nothing to do"
        sys.exit(0)

amount = 0
failed = 0
passed = 0
result = []

for root, dirs, files in os.walk(TargetPath):
	for f in files:
		if f.endswith(".trs"):
			p = root + "/" + f
			#print p
			amount += 1
			t = {
				"test": f[:-len(".trs")],
				"output": root + "/" + f[:-len(".trs")] + ".log"
			}

			with open(p, "r") as x:
				d = yaml.load(x)
				t["result"] = d [':test-result']
				if d[':test-result'] == 'FAIL':
					failed +=1
				else:
					passed +=1
			result.append(t)

test_class = "make-check"
top = Element('testsuite', { 'name': 'make-check'})
for t in result:
        c  = SubElement(top, 'testcase', {
                'name': t['test'],
                'classname': test_class,
                #'time': ''
                })
        s = SubElement(c, 'system-out')
        s.text = "[[ATTACHMENT|" + t['output'] + "]]"
        if t['result'].lower() == 'fail':
                f = SubElement(c, 'failure')

from xml.etree import ElementTree
from xml.dom import minidom

r = minidom.parseString(ElementTree.tostring(top, 'utf-8'))
if OutputDirPath == None:
	print r.toprettyxml(indent="  ")
else:
	with open(OutputDirPath + "/" + test_class + ".xml", 'w') as xml:
        	xml.write(r.toprettyxml(indent="  "))
	print str(amount) + " (total) = " + str(passed) + " (passed) + " + str(failed) + " (failed)"

