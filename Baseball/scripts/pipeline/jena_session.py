"""Process-scoped Jena SHACL session; no network service or persistent JVM."""
import base64
from pathlib import Path
import queue
import subprocess
import tempfile
import threading
import time
from rdflib import Graph


class Session:
    def __init__(self, data_path, java, classpath, timeout=300):
        self.data_path=Path(data_path).resolve(); self.java=Path(java).resolve()
        self.classpath=Path(classpath).resolve(); self.timeout=timeout; self.process=None
        self.timings=[]

    def __enter__(self):
        self.errors=tempfile.TemporaryFile()
        self.process=subprocess.Popen([str(self.java),'-Xms64m','-Xmx384m','-cp',str(self.classpath),
            str(Path(__file__).with_name('ShaclSession.java')),self.data_path.as_uri()],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.errors)
        self.lines=queue.Queue()
        def read():
            try:
                for line in iter(self.process.stdout.readline,b''): self.lines.put(line)
            finally: self.lines.put(None)
        threading.Thread(target=read,daemon=True).start()
        try:
            ready=self.line().split('\t')
            if len(ready)!=2 or ready[0]!='READY': raise RuntimeError('Jena session did not load its data graph')
            self.data_count=int(ready[1]); return self
        except BaseException:
            self.__exit__(None,None,None); raise

    def line(self):
        try: line=self.lines.get(timeout=self.timeout)
        except queue.Empty: raise TimeoutError('Jena SHACL session exceeded its bounded stage timeout')
        if line is None:
            self.errors.seek(0)
            raise RuntimeError('Jena SHACL session exited: '+self.errors.read()[-4000:].decode('utf-8','replace'))
        return line.decode('utf-8').rstrip('\r\n')

    def validate_with_jena(self, *, data_path, shape_path, java, classpath, max_heap):
        if (Path(data_path).resolve()!=self.data_path or Path(java).resolve()!=self.java
                or Path(classpath).resolve()!=self.classpath or max_heap!='384m'):
            raise ValueError('SHACL session inputs differ from the requested validation')
        started=time.perf_counter()
        self.process.stdin.write(base64.b64encode(Path(shape_path).resolve().as_uri().encode())+b'\n')
        self.process.stdin.flush()
        fields=self.line().split('\t',3)
        if len(fields)!=4 or fields[0]!='REPORT' or fields[1] not in ('true','false'):
            raise RuntimeError('Invalid SHACL session response')
        text=base64.b64decode(fields[3],validate=True).decode('utf-8')
        report=Graph().parse(data=text,format='turtle')
        conforms=fields[1]=='true'
        self.timings.append(dict(shape=str(shape_path),seconds=round(time.perf_counter()-started,3),
            shapeTriples=int(fields[2]),conforms=conforms))
        return conforms,report,text

    def __exit__(self,*unused):
        if self.process:
            self.process.stdin.close()
            try: self.process.wait(timeout=5)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
            self.process.stdout.close()
        self.errors.close()
