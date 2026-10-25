#!/usr/bin/env python3
"""Fetch only pinned official Debian packages from the checked-in manifests.
For a Debian 13 x86_64 build host. No sudo or system writes are used.
"""
from pathlib import Path
import concurrent.futures, hashlib, json, lzma, re, subprocess, sys
base=Path(__file__).resolve().parent.parent
cache=base/'toolchains/debian'; cache.mkdir(parents=True,exist_ok=True)
root=cache/'root'; root.mkdir(exist_ok=True)
manifests=base/'manifests'
# gpgv and the official archive keyring must already be trusted prerequisites.
subprocess.run(['gpgv','--keyring','/usr/share/keyrings/debian-archive-keyring.gpg',str(manifests/'debian-trixie-InRelease')],check=True)
release=(manifests/'debian-trixie-InRelease').read_text()
records=[]
for arch, name in [('amd64','debian-amd64.json'),('riscv64','debian-riscv64-openssl.json')]:
 index_path=manifests/f'Packages-{arch}.xz'
 if not index_path.exists():
  subprocess.run(['curl','-fLsS','--max-time','180',f'https://deb.debian.org/debian/dists/trixie/main/binary-{arch}/Packages.xz','-o',str(index_path)],check=True)
 data=index_path.read_bytes()
 digest=hashlib.sha256(data).hexdigest()
 if not re.search(rf'^ {digest} +{len(data)} main/binary-{arch}/Packages.xz$',release,re.M):
  raise RuntimeError(f'{arch} Packages index is not authenticated by InRelease')
 index={}
 for entry in lzma.decompress(data).decode().split('\n\n'):
  d={}
  for line in entry.splitlines():
   if line and not line[0].isspace() and ': ' in line:
    key,value=line.split(': ',1); d[key]=value
  if 'Package' in d:index[d['Package']]=d
 for record in json.loads((manifests/name).read_text()):
  actual=index.get(record['Package'],{})
  if any(actual.get(k)!=record.get(k) for k in ['Package','Version','Filename','Size','SHA256']):
   raise RuntimeError(f'Package manifest mismatch: {record["Package"]}')
  records.append(record)
def fetch(d):
 p=cache/Path(d['Filename']).name
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=d['SHA256']:
  subprocess.run(['curl','-fLsS','--retry','2','--max-time','180','https://deb.debian.org/debian/'+d['Filename'],'-o',str(p)],check=True)
 if hashlib.sha256(p.read_bytes()).hexdigest()!=d['SHA256']:
  raise RuntimeError(f'Package checksum mismatch: {p}')
 return p
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: paths=list(pool.map(fetch,records))
if '--verify-only' in sys.argv:
 print('Authenticated signatures, both package indexes and',len(paths),'package hashes; no extraction performed.')
else:
 for p in paths: subprocess.run(['dpkg-deb','-x',str(p),str(root)],check=True)
 print('Extracted',len(paths),'authenticated Debian packages to',root)
