import sys
import docopt
import re
#import yaml
import json
import os
import shutil

doc = """
Usage:
    saw-teuthology-logs <path> [options]

Options:

  -o <path>, --output <path>            save report to a file
"""

args = docopt.docopt(doc, argv=sys.argv[1:])

print(args)
input_path=args.get('<path>')
output_path=args.get('--output') or "saw-job-log.output.html"
templates_name = output_path[max(output_path.rfind('/'),0):output_path.rfind('.')] + '.tmp'

#templates_dir=os.path.dirname(os.path.abspath(__file__)) + 'saw-job-log-jinja2-templates/logs'

templates_root_dir=os.getcwd() + '/' + templates_name
templates_dir=templates_root_dir + '/logs'

if not os.path.isdir(templates_dir):
    os.makedirs(templates_dir)

shutil.copyfile(os.path.dirname(os.path.abspath(__file__)) + '/jinja2/saw-job-log.jinja2', templates_root_dir + '/saw-job-log.jinja2')
def saw_log(line, number, obj):
    if 'teuthology.run_tasks:' in line:
        if 'Running task' in line:
            obj.set_running()
            m = re.match(r".*Running task (?P<task>[\w.-]+)\.\.\..*", line)
            task = m.group('task')
            print("Running %s" % task, x, line, end='')
            task_id = len(obj.stack)+1
            running_log = "%s/log-%02i-%s.running.txt" % (templates_dir, task_id, task)
            cleanup_log = "%s/log-%02i-%s.cleanup.txt" % (templates_dir, task_id, task)
            obj.tasks += [{
                'name': task,
                'id': task_id,
                'running_log': open(running_log, 'w'),
                'cleanup_log': open(cleanup_log, 'w'),
                'running_log_name': running_log[running_log.rfind('/'):],
                'cleanup_log_name': cleanup_log[cleanup_log.rfind('/'):],
                'running': {'start': number, 'end': None},
                'cleanup': {'start': None, 'end': None},
            }]
            obj.stack.append(task)
            print(obj.stack)
            if len(obj.stack)>0:
                print(obj.stack[-1])
            obj.task_index = len(obj.stack)-1
        elif 'Unwinding manager' in line:
            obj.set_cleanup()
            m = re.match(r".*Unwinding manager (?P<task>[\w.-]+).*", line)
            task = m.group('task')
            print("Cleanup %s" % task, x, line, end='')
            tip_index = len(obj.stack) - 1
            tip = obj.stack[tip_index]
            obj.tasks[tip_index]['cleanup']['end'] = number
            if tip == task:
                pos=tip_index
                obj.stack.pop()
            else:
                def rindex(mylist, myvalue):
                    return len(mylist) - mylist[::-1].index(myvalue) - 1
                pos=rindex(obj.stack, task)
                print("===========> Tip %s does not match task %s" % (tip, task))
                print("WARNNIG: No cleanup for tasks: %s" % obj.stack[pos+1:])
                obj.stack=obj.stack[:pos]
            obj.tasks[pos]['cleanup']['start'] = number
            obj.cleanup_task = pos
            print("STACK: %s" % ' -> '.join(obj.stack))
    elif 'teuthology.run:Summary' in line:
        obj.set_finish()
    else:
        if 'teuthology.run:pass' in line:
            obj.result = True
        elif 'teuthology.run:FAIL' in line:
            obj.result = False
        if len(obj.stack) >= 0:
            task_index = obj.task_index
            if obj.is_running():
                task = obj.tasks[task_index]
                task['running']['end'] = number
                task['running_log'].write(line)
            if obj.is_cleanup():
                task = obj.tasks[obj.cleanup_task]
                task['cleanup']['end'] = number
                task['cleanup_log'].write(line)
            if obj.is_finish():
                print(line, end='')
                
                
class Log:
    tasks = []
    stack = []
    # running, cleanup
    scope = None
    task_index = 0
    cleanup_task = None
    result = None
    def is_running(self):
        return self.scope == 'running'
    def is_cleanup(self):
        return self.scope == 'cleanup'
    def is_finish(self):
        return self.scope == 'finish'
    def set_running(self):
        self.scope = 'running'
    def set_cleanup(self):
        self.scope = 'cleanup'
    def set_finish(self):
        self.scope = 'finish'

with open(input_path) as f:
    x=0
    obj = Log()
    for i in f.readlines():
        #print(x, i, end='')
        saw_log(i, x, obj)
        x += 1
                
        #print("%i %s" % (x, i))
    for task in obj.tasks:
        task['running_log'].flush()
        task['cleanup_log'].flush()

    print(json.dumps([{'name': i['name'], 
                       'running': i['running'], 
                       'cleanup': i['cleanup']} for i in obj.tasks], indent='  '))
    print(obj.stack)

import jinja2

# logs teuthology log directory
# it contains subdirectories corresponding to jobs


@jinja2.contextfunction
def include_file(ctx, name):
    env = ctx.environment
    return jinja2.Markup(env.loader.get_source(env, name)[0])

#loader = jinja2.PackageLoader(__name__, templates_root_dir)
loader = jinja2.FileSystemLoader(templates_root_dir)

env = jinja2.Environment(loader=loader, autoescape=(['html','xml']))
env.globals['include_file'] = include_file
#with open('saw-job-log.jinja2') as f:
#    t = env.get_template(f.readlines())
#    r = t.render(tasks=obj.tasks)
#    print(r)
t = env.get_template('saw-job-log.jinja2')
r = t.generate(tasks=obj.tasks, passed=obj.result)
print("Saving report to %s" % output_path)
with open(output_path, 'w') as o:
    for i in r:
        o.write(i)

task_names = [i['name'] == 'install' for i in obj.tasks]
install_index = task_names.index(True)

task_trace = (i['name'] for i in obj.tasks[install_index:])

print("Steps: %s" % " > ".join(task_trace) + (' [passed]' if obj.result else ' [failed]'))

