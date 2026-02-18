import hashlib, os
from pathlib import Path

def ensure_dir(p:str)->None:
    Path(p).mkdir(parents=True, exist_ok=True)

def sha256_file(path:str)->str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write_bytes(path:str, content:bytes):
    ensure_dir(os.path.dirname(path))
    with open(path,'wb') as f:
        f.write(content)
