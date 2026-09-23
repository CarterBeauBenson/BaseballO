"""Conservative reconciliation of progress left by terminated local workers."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


def alive(pid):
    if type(pid) is not int or pid <= 0: return None
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
        handle = kernel.OpenProcess(0x1000,False,pid)
        if not handle: return False if ctypes.get_last_error()==87 else None
        try:
            code=ctypes.c_uint32()
            return code.value==259 if kernel.GetExitCodeProcess(handle,ctypes.byref(code)) else None
        finally: kernel.CloseHandle(handle)
    try: os.kill(pid,0); return True
    except ProcessLookupError: return False
    except PermissionError: return None


def reconcile(path, is_alive=alive):
    path=Path(path)
    before=path.read_bytes(); record=json.loads(before)
    if record.get('status')!='running' or is_alive(record.get('processId')) is not False:
        return record
    record.update(status='interrupted',reason='WORKER_PROCESS_EXITED',
        reconciledAtUtc=datetime.now(timezone.utc).isoformat())
    # An observer must never overwrite a concurrent worker checkpoint.
    if path.read_bytes()!=before: return json.loads(path.read_bytes())
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=path.parent,delete=False) as out:
        json.dump(record,out,indent=2); out.flush(); os.fsync(out.fileno()); temporary=Path(out.name)
    try: os.replace(temporary,path)
    finally: temporary.unlink(missing_ok=True)
    return record


def reconcile_builds(state):
    paths=list((Path(state)/'serving/builds').glob('*.progress.json'))
    dashboard=Path(state)/'serving/dashboard/progress.json'
    if dashboard.is_file(): paths.append(dashboard)
    return [dict(path=str(path),status=reconcile(path).get('status')) for path in paths]
