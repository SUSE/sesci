# Convert ctest logs to junit format
import sys
import re
import os

from xml.etree.ElementTree import Element, SubElement, Comment, tostring

LogFilePath = 'build/Testing/Temporary/LastTest.log'

if (len(sys.argv) > 1):
	LogFilePath = sys.argv[1]
OutputDirPath = 'res'
if (len(sys.argv) > 2):
	OutputDirPath = sys.argv[2]
try:
	os.stat(OutputDirPath)
except:
	os.mkdir(OutputDirPath)

try:
	os.stat(LogFilePath)
except:
	print "Log file [" + LogFilePath + "] does not exists. Nothing to do"
	sys.exit(0)


state = 'start'

results = []
test_result = ''
test_index = ''
test_name = ''
test_time = 0
output_length = 0
output_filename = ''
outputfile = 0
test_class = 'make-check'
with open(LogFilePath, 'r') as logfile:
	for l in logfile:
		if   state is 'start':
			if l.find('Start testing:') == 0:
				print "Hurra"
				state = 'test'
			else: 
				break
		elif state is 'test':
			if l.find('----') == 0:
				print ">>>>>>>>>>>>>"
			if l.find('Test:') > 0:
				m = re.match(r"(\d+)/(\d+) Test: (.*)$", l)
				print 'Test ' + m.group(1) + ': ' + m.group(3)
				test_name = m.group(3)
				test_index = m.group(1)
			if l.find('Command:') == 0:
				print l
			if l.find('Directory:') == 0:
				print l
			if l.find('Output:') == 0:
				outdir = OutputDirPath + '/' + 'output' + '/' + test_name
				try:
					os.stat(outdir)
				except:
					os.makedirs(outdir)
				output_filename = outdir+ '/' + test_name + '-out.txt'
				outputfile = open(output_filename, 'w')
				state = 'readoutput'
			if l.find('End testing: ') == 0:
				print l
				print "Parsing done"
		elif state is 'readoutput':
			if l.find('<end of output>') == 0:
				print 'Output length is ', output_length
				outputfile.close()
				output_length = 0
				state = 'wait for time'
			else:
				output_length += len(l)
				outputfile.write(l)
				
		elif state is 'wait for time':
			if l.find('Test time = ') == 0:
				m = re.match(r"Test time =\s+(.*) (sec)", l)
				test_time = m.group(1)
				state = 'wait for result'
		elif state is 'wait for result':
			if l.find('Test Passed.') == 0 or l.find('Test Failed.') == 0:
				m = re.match(r"Test (\w+).", l)
				test_result = m.group(1)
				print l
				state = 'wait test end'
		elif state is 'wait test end':
			if l.find('---') == 0:
				results.append({
					"test": test_name, 
					"result": test_result,
					"output": output_filename,
					"time"  : test_time,
					})
				test_time = 0
				state = 'test'


top = Element('testsuite', { 'name': 'make-check'})
for t in results:
	c  = SubElement(top, 'testcase', {
		'name': t['test'], 
		'classname': test_class,
		'time': t['time'],
		})
#	print t['result'].lower()
	s = SubElement(c, 'system-out')
	s.text = "[[ATTACHMENT|" + t['output'] + "]]"
	if t['result'].lower() == 'failed':
		f = SubElement(c, 'failure')
		print t['test'], t['result']


from xml.etree import ElementTree
from xml.dom import minidom


r = minidom.parseString(ElementTree.tostring(top, 'utf-8'))
print r.toprettyxml(indent="  ")

with open(OutputDirPath + "/" + test_class + ".xml", 'w') as xml:
	xml.write(r.toprettyxml(indent="  "))

