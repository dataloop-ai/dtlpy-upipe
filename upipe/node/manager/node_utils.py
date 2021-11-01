import os
import psutil


def kill_process(pid):
    if pid is None or pid == 0:
        return
    try:
        p = psutil.Process(pid)
        p.terminate()  # or p.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return


def kill_by_path(process_path):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    process = get_process_by_path(process_path)
    if not process:
        raise EnvironmentError("kill_by_path : process want not found")
    print(f"Closing old process : {process_path} ({process.pid})")
    process_pid = process.pid
    return kill_process(process_pid)


def get_process_by_path(process_path):
    processes = get_all_process_by_path(process_path)
    if len(processes):
        return processes[0]
    return None


def get_all_process_by_path(process_path):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    processes = []
    for p in psutil.process_iter():
        try:
            cmdline = p.cmdline()
            if process_path in cmdline:
                processes.append(p)
        except psutil.AccessDenied:
            continue
    return processes


def count_process_by_path(process_path):
    return len(get_all_process_by_path(process_path))


def kill_em_all(process_path, but_me=True):
    if not process_path:
        raise ValueError("kill_by_path : path must be a valid process path")
    killed = 0
    for process in psutil.process_iter():
        try:
            cmdline = process.cmdline()
            if process_path in cmdline:
                if process.pid == os.getpid() and but_me:
                    continue
                kill_process(process.pid)
                killed += 1
        except psutil.AccessDenied:
            continue
    return killed


def kill_port_listener(port: int):
    for process in psutil.process_iter():
        for conns in process.connections(kind='inet'):
            if conns.laddr.port == port:
                kill_process(process.pid)
