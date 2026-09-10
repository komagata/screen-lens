"""Bounded local OCR message framing, no file paths or serialized Python objects."""
import struct
import time

MAX_BYTES = 48 * 1024 * 1024

def send(connection, payload):
    if len(payload)>MAX_BYTES:raise ValueError('OCR message too large')
    connection.sendall(struct.pack('!I',len(payload))+payload)

def receive(connection, timeout=10):
    deadline=time.monotonic()+timeout
    previous=connection.gettimeout()
    def read(count):
        parts=[]
        while count:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('OCR message deadline exceeded')
            connection.settimeout(remaining)
            chunk=connection.recv(count)
            if not chunk:raise EOFError('Truncated OCR message')
            parts.append(chunk);count-=len(chunk)
        return b''.join(parts)
    try:
        size=struct.unpack('!I',read(4))[0]
        if size>MAX_BYTES:raise ValueError('OCR message too large')
        return read(size)
    finally:
        connection.settimeout(previous)
