"""Private, bounded-lifetime local OCR service."""
import fcntl
import io
import json
import os
from pathlib import Path
import socket
import stat
import struct
from ocr_transport import receive, send

def serve(directory, factory, *, idle_timeout=120):
    """Own the lock for the entire server lifetime; factory constructs one recognizer."""
    directory=Path(directory)
    info=directory.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
        raise PermissionError('OCR service needs an owned private directory')
    fd=os.open(directory/'ocr.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'rb') as lock:
        info=os.fstat(lock.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode & 0o077:
            raise PermissionError('Unsafe OCR lock file')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return False
        path=directory/'ocr.sock'
        if path.exists() or path.is_symlink():
            info=path.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid!=os.getuid():
                raise RuntimeError('Refusing to replace non-owned socket path')
            path.unlink()
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
            listener.bind(str(path));os.chmod(path,0o600)
            identity=path.lstat().st_ino
            try:
                listener.listen(1);listener.settimeout(idle_timeout)
                recognize=factory()
                recognitions=0
                while True:
                    try:connection,_=listener.accept()
                    except TimeoutError:return True
                    with connection:
                        connection.settimeout(10)
                        try:
                            _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                            if uid!=os.getuid():continue
                            payload=receive(connection)
                            if not payload:
                                send(connection,json.dumps(dict(ready=True,protocol=1,pid=os.getpid(),recognitions=recognitions)).encode())
                                continue
                            from PIL import Image
                            with Image.open(io.BytesIO(payload)) as source:
                                if source.format!='PNG' or source.width*source.height>20_000_000:
                                    raise ValueError('Unsupported screenshot')
                                image=source.convert('RGB')
                            try:
                                result=recognize(image)
                                recognitions+=1
                            finally:image.close()
                            send(connection,json.dumps(dict(rows=result),ensure_ascii=False).encode())
                            del result,payload
                        except Exception:
                            # No payload, paths, credentials or library error details in replies.
                            try:send(connection,b'{"error":"ocr_request_failed"}')
                            except OSError:pass
                        finally:
                            payload=None
                            result=None
            finally:
                try:
                    if path.lstat().st_ino==identity:path.unlink()
                except FileNotFoundError:pass

def recognizer():
    from ocr_backends import make_rapid
    from ocr_frame_cache import OcrFrameCache
    from live import local_ocr
    engine=make_rapid('v6',intra_threads=8,detector_limit='max',cuda=True)
    # Reuse the model, not screenshots or OCR results, across clients.
    return lambda image:local_ocr(image,engine,dict(ocr_profile='v6'),OcrFrameCache())

if __name__=='__main__':
    import sys
    if len(sys.argv)!=2:raise SystemExit('Usage: ocr_service.py PRIVATE_RUNTIME_DIRECTORY')
    serve(Path(sys.argv[1]),recognizer)
