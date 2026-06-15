import os, tempfile

LOG_FILE = os.path.join(tempfile.gettempdir(), 'warnings_debug.log')

def _write(msg):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
        f.flush()

def write_run(task, stage):
    _write(f"RUN called: task_id={task.id}, status={task.status}, stage={stage}")

def write_warn(task, warnings):
    import json
    _write(f"STORING warnings for task {task.id}: {json.dumps(warnings)}")

def write_commit(task):
    _write(f"COMMITTED task {task.id}, warnings={task.warnings}")

def write_empty(task):
    _write(f"NO WARNINGS for task {task.id}")
