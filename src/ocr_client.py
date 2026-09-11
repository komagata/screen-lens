"""Client for the optional private resident OCR process."""
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import stat
import struct
import subprocess
import sys
import time
from ocr_transport import receive,send

ROOT=Path(__file__).resolve().parent

def validate_rows(rows):
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError('Invalid OCR rows')
    ids=set()
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Invalid OCR row')
        if not isinstance(row.get('id'),str) or row['id'] in ids:raise ValueError('Invalid OCR ID')
        ids.add(row['id'])
        if not isinstance(row.get('text'),str) or len(row['text'])>10000:raise ValueError('Invalid OCR text')
        for key in ('x','y','width','height','confidence'):
            value=row.get(key)
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Invalid OCR geometry')
        if row['width']<=0 or row['height']<=0 or not 0<=row['confidence']<=1:
            raise ValueError('Invalid OCR dimensions/confidence')
    return rows

class Client:
    def __init__(self,directory=None):
        if directory is None:
            version=hashlib.sha256()
            for name in ('ocr_client.py','ocr_service.py','ocr_transport.py','ocr_backends.py','live.py','ocr_frame_cache.py'):
                version.update((ROOT/name).read_bytes())
            directory=Path(os.environ['XDG_RUNTIME_DIR'])/('screen-lens-ocr-'+version.hexdigest()[:12])
        self.directory=Path(directory)
        self.directory.mkdir(mode=0o700,exist_ok=True)
        info=self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise PermissionError('Unsafe OCR runtime directory')
        self.path=self.directory/'ocr.sock'
        self.child=None
        self.readiness={}

    def call(self,payload,timeout=10):
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as connection:
            connection.settimeout(timeout);connection.connect(str(self.path))
            _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=os.getuid():raise PermissionError('Wrong OCR service owner')
            send(connection,payload)
            result=json.loads(receive(connection,timeout))
            if not isinstance(result,dict) or 'error' in result:raise ValueError('OCR service rejected request')
            return result

    def ensure_running(self):
        def ready():
            result=self.call(b'',timeout=.5)
            if result.get('protocol')!=1 or result.get('ready') is not True:
                raise ValueError('Incompatible OCR service')
            self.readiness={k:result[k] for k in ('pid','recognitions')
                            if type(result.get(k)) is int and result[k]>=0}
        try:ready();return
        except OSError:pass
        # Service lifetime lock arbitrates concurrent starters. Never kill a peer.
        self.child=subprocess.Popen([sys.executable,str(ROOT/'ocr_service.py'),str(self.directory)],
            stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            start_new_session=True)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            try:ready();return
            except OSError:
                status=self.child.poll()
                if status not in (None,0):raise RuntimeError('OCR service startup failed')
                time.sleep(.05)
        raise TimeoutError('OCR service startup timed out')

    def recognize(self,png):
        result=self.call(png)
        return validate_rows(result.get('rows'))
