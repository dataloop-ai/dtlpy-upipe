import time
from datetime import datetime
import json
import os.path
import tempfile
import os
from .node_utils import kill_process


def get_timestamped_object():
    obj = {}
    obj['log_time'] = time.mktime(datetime.utcnow().timetuple()) * 1000
    obj['created_time_str'] = datetime.now().strftime("%H:%M:%S")
    obj['creator_pid'] = os.getpid()
    return obj


class PidLog:
    def __init__(self):
        temp_dir = tempfile.gettempdir()
        self.log_file = os.path.join(temp_dir, "upipe_pid_log.json")
        print(f"upipe pid log:{self.log_file}")
        self.log = {}
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    self.log = json.load(f)
            except Exception:
                os.unlink(self.log_file)
                self.log = {}

    def log_pid(self, pid, name):
        pid = str(pid)
        if len(self.log) > 1:
            raise IndexError("Process log contains more than one session")
        session_pid = list(self.log.keys())[0]
        if 'pids' not in self.log[session_pid]:
            raise ProcessLookupError(f"Session pid list corrupted")
        if pid in self.log[session_pid]['pids']:
            return
        log_entry = get_timestamped_object()
        log_entry['pid'] = pid
        log_entry['name'] = name
        self.log[session_pid]['pids'][pid] = log_entry
        self._save()

    def _clean_session(self, root_pid):
        root_pid = str(root_pid)
        if not self.log[root_pid]:
            return
        session_log = self.log[root_pid]
        if 'pids' not in session_log:
            return
        for pid in session_log['pids']:
            kill_process(pid)
        del self.log[root_pid]
        self._save()

    def start_session(self, root_pid):
        root_pid = str(root_pid)
        sessions_to_clean = []
        for pid in self.log:
            if pid == root_pid:
                continue
            sessions_to_clean.append(pid)
        for pid in sessions_to_clean:
            self._clean_session(pid)
        if root_pid not in self.log:
            new_session_obj = get_timestamped_object()
            new_session_obj['pids'] = {}
            self.log[root_pid] = new_session_obj
        self._save()

    def _save(self):
        with open(self.log_file, 'w') as outfile:
            json.dump(self.log, outfile, indent=4)


pid_log = PidLog()
