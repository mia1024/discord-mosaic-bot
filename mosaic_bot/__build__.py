"""
Stub file for build ID. Will be overwritten during build process
"""

from hashlib import sha1
import os, pathlib
import datetime

hasher = sha1()
top=pathlib.Path(__file__).resolve().parent
for root, dir, files in os.walk(top):
    for fp in files:
        if fp.endswith('.py'):
            with open(top / root / fp, 'rb') as f:
                hasher.update(f.read())

build_hash = hasher.hexdigest()
build_type = 'staging' if 'docker' in open('/proc/1/cgroup').read() else 'development'
build_time = datetime.datetime.utcnow().isoformat()