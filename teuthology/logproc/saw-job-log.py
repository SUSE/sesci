import sys
import docopt
import re
#import yaml
import json
import os
import shutil
import logging
import jinja2

doc = """
Usage:
    saw-teuthology-logs <path> [options]

Options:

  -o <path>, --output <path>            save report to a file
  -r <run>, --run <run>                 run name
  -j <job>, --job <job>                 job name
  -d <desc>, --desc <desc>              job description
  -a <path>, --archive <path>           relative path to job archive
  -p, --partial                         ranged index html
  -v, --verbose                         verbose logging
"""

args = docopt.docopt(doc, argv=sys.argv[1:])

if args.get('--verbose'):
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)
logging.debug(f'Command line arguments: {args}')
input_path=args.get('<path>')
if args.get('--partial'):
   output_path=input_path + '.html'
   job_archive='.'
else:
   output_path=args.get('--output') or "saw-job-log.output.html"
   job_archive=args.get('--archive') or ""
templates_name = output_path[max(output_path.rfind('/'),0):output_path.rfind('.')] + '.tmp'

#templates_dir=os.path.dirname(os.path.abspath(__file__)) + 'saw-job-log-jinja2-templates/logs'

templates_root_dir=os.getcwd() + '/' + templates_name
templates_dir=templates_root_dir + '/logs'

if not os.path.isdir(templates_dir):
    os.makedirs(templates_dir)

if args.get('--partial'):
    shutil.copyfile(os.path.dirname(os.path.abspath(__file__)) + '/jinja2/saw-job-index.jinja2', templates_root_dir + '/saw-job-log.jinja2')
else:
    shutil.copyfile(os.path.dirname(os.path.abspath(__file__)) + '/jinja2/saw-job-log.jinja2', templates_root_dir + '/saw-job-log.jinja2')
def saw_log(line, number, obj, byte_offset=0, byte_size=0):
    if 'teuthology.run_tasks:' in line and 'Running task' in line:
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
                'running': {'start': number, 'end': number, 'start_offset': byte_offset, 'end_offset': byte_offset + byte_size},
                'cleanup': {'start': None, 'end': None, 'start_offset': None, 'end_offset': None},
            }]
            obj.stack.append(task)
            logging.debug(f'stack: {obj.stack}')
            if len(obj.stack)>0:
                logging.debug(f'* {obj.stack[-1]}')
            obj.task_index = len(obj.stack)-1
    elif 'teuthology.run_tasks:' in line and 'Unwinding manager' in line:
            if obj.cleanup_task:
                print("===============> Found the end of task '%s' cleanup on line %s" % (obj.tasks[obj.cleanup_task]['name'], number - 1))
                obj.tasks[obj.cleanup_task]['cleanup']['end'] = number-1
                obj.tasks[obj.cleanup_task]['cleanup']['end_offset'] = byte_offset
            obj.set_cleanup()
            m = re.match(r".*Unwinding manager (?P<task>[\w.-]+).*", line)
            task = m.group('task')
            tip_index = len(obj.stack) - 1
            tip = obj.stack[tip_index]
            print("===> Cleanning up task %s" % task, x, line, end='')
            if tip == task:
                pos=tip_index
                obj.stack.pop()
            else:
                def rindex(mylist, myvalue):
                    return len(mylist) - mylist[::-1].index(myvalue) - 1
                pos=rindex(obj.stack, task)
                print("====> Tip %s does not match task %s" % (tip, task))
                print("======> Found task %s at position %s in stack" % (task, pos))
                print("WARNNIG: No cleanup for tasks: %s" % obj.stack[pos+1:])
                obj.stack=obj.stack[:pos]
            print("======> Found task '%s' cleanup start at %s line" % (obj.tasks[pos]['name'], number))
            obj.tasks[pos]['cleanup']['start'] = number
            obj.tasks[pos]['cleanup']['start_offset'] = byte_offset
            obj.cleanup_task = pos
            print("STACK: %s" % ' -> '.join(obj.stack))
    elif 'teuthology.run:Summary' in line:
        #task = obj.tasks[obj.cleanup_task]
        #logging.debug(f"cleanup task {task['name']} finished in the end")
        #obj.tasks[obj.cleanup_task]['cleanup']['end'] = number
        #obj.tasks[obj.cleanup_task]['cleanup']['end_offset'] = byte_offset + byte_size

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
                task['running']['end_offset'] = byte_offset + byte_size
                task['running_log'].write(line)
            if obj.is_cleanup():
                task = obj.tasks[obj.cleanup_task]
                task['cleanup']['end'] = number
                task['cleanup']['end_offset'] = byte_offset
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

with open(input_path, 'rb') as f:
    x=0
    _offset=0
    obj = Log()
    for i in f.readlines():
        _size = len(i)
        saw_log(i.decode(), x, obj, byte_offset=_offset, byte_size=_size)
        x += 1
        _offset += _size
    for task in obj.tasks:
        task['running_log'].flush()
        task['cleanup_log'].flush()

    json_dump = json.dumps([{'name': i['name'],
                       'running': i['running'],
                       'cleanup': i['cleanup']} for i in obj.tasks], indent='  ')
    logging.debug(f"Dump: {json_dump}")
    logging.info(f"Stack: {obj.stack}")
with open(os.path.dirname(input_path) + '/teuthology.log.json', 'w+') as f:
    f.write(json_dump)

# logs teuthology log directory
# it contains subdirectories corresponding to jobs


@jinja2.contextfunction
def include_file(ctx, name):
    env = ctx.environment
    return jinja2.Markup.escape(env.loader.get_source(env, name)[0])

#loader = jinja2.PackageLoader(__name__, templates_root_dir)
loader = jinja2.FileSystemLoader(templates_root_dir)

env = jinja2.Environment(loader=loader, autoescape=jinja2.select_autoescape(['html','xml','htm']))
env.globals['include_file'] = include_file
#with open('saw-job-log.jinja2') as f:
#    t = env.get_template(f.readlines())
#    r = t.render(tasks=obj.tasks)
#    print(r)
t = env.get_template('saw-job-log.jinja2')
r = t.generate(
        tasks=obj.tasks,
        passed=obj.result,
        run_name=args.get('--run') or "^",
        job_log=os.path.relpath(os.path.abspath(input_path), start=os.path.abspath(os.path.dirname(output_path))),
        job_name=args.get('--job') or "",
        job_archive=job_archive,
        job_description=args.get('--desc') or "",
        )
logging.info(f"Saving report to {output_path}")
with open(output_path, 'w') as o:
    for i in r:
        o.write(i)

task_names = [i['name'] == 'install' for i in obj.tasks]
install_index = task_names.index(True)

task_trace = (i['name'] for i in obj.tasks[install_index:])

logging.info("Steps: %s" % " > ".join(task_trace) + (' [passed]' if obj.result else ' [failed]'))

