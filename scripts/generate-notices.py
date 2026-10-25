#!/usr/bin/env python3
"""Generate target-specific Cargo notices; never silently ignore unknown licenses.
Prerequisites: pinned source checkout, Cargo dependencies fetched, cargo-about 0.9.2
installed with `cargo install cargo-about --version 0.9.2 --locked --features cli`.
Native/embedded and Rust-standard-library supplements are reviewed separately.
"""
import argparse, hashlib, json, os, re, subprocess, tomllib
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'src/codex-rs');parser.add_argument('--cargo-home',type=Path,default=Path(os.environ.get('CARGO_HOME',str(Path.home()/'.cargo'))));parser.add_argument('--harvest-only',action='store_true');args=parser.parse_args()
src=args.source.resolve(); out=ROOT/'licenses';out.mkdir(exist_ok=True)
def cargo(*args):return subprocess.check_output(['cargo',*args],cwd=src,text=True)
meta=json.loads(cargo('metadata','--locked','--format-version','1','--filter-platform','riscv64gc-unknown-linux-gnu'))
tree=cargo('tree','--locked','-p','codex-cli','--target','riscv64gc-unknown-linux-gnu','-e','normal,build','--prefix','none','--format','{p}')
selected=set()
for line in tree.splitlines():
 match=re.match(r'([^ ]+) v([^ ]+)',line)
 if match:selected.add(match.groups())
pkgs=[p for p in meta['packages'] if (p['name'],p['version']) in selected]
missing=selected-{(p['name'],p['version']) for p in pkgs}
# Cargo's target-filtered metadata can omit host-only build dependencies. Use
# their exact downloaded registry manifests, not an inferred generic license.
for name,version in sorted(missing):
 paths=list((args.cargo_home/'registry/src').glob(f'*/{name}-{version}/Cargo.toml'))
 if len(paths)!=1:raise RuntimeError(f'Missing/ambiguous manifest for {name} {version}')
 manifest=tomllib.loads(paths[0].read_text());p=manifest['package'];pkgs.append(dict(name=name,version=version,license=p.get('license'),license_file=p.get('license-file'),repository=p.get('repository'),source='registry+https://github.com/rust-lang/crates.io-index',manifest_path=str(paths[0])))
notices={};inventory=[];no_files=[]
for p in sorted(pkgs,key=lambda x:(x['name'],x['version'])):
 base=Path(p['manifest_path']).parent
 if p.get('source') is None:
  inventory.append(dict(name=p['name'],version=p['version'],license=p.get('license'),source='https://github.com/openai/codex/tree/970111f6cb62cc02fe36a82ea7d71b37a2889c97',notice='See repository LICENSE and NOTICE.'));continue
 candidates=[]
 for directory,dirs,files in os.walk(base):
  dirs[:]=[d for d in dirs if d not in {'.git','target','node_modules'}]
  for name in files:
   if re.match(r'^(licen[cs]e|copying|notice|copyright|unlicense)(?:[._-]|$)',name,re.I) or Path(directory).name.lower() in {'license','licenses'}:
    path=Path(directory)/name
    if not path.is_symlink() and path.is_file() and path.stat().st_size<5_000_000:candidates.append(path)
 if p.get('license_file'):
  path=Path(p['license_file']);path=path if path.is_absolute() else base/path
  if path.is_file():candidates.append(path)
 # Git workspaces often keep a license above the individual crate directory.
 if str(p.get('source','')).startswith('git+'):
  parent=base
  for _ in range(8):
   candidates += [x for x in parent.iterdir() if x.is_file() and re.match(r'^(licen[cs]e|copying|notice|copyright|unlicense)(?:[._-]|$)',x.name,re.I)]
   if (parent/'.git').exists():break
   parent=parent.parent
 files=[]
 for path in sorted(set(candidates)):
  data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();text=data.decode('utf-8',errors='replace')
  try:relative=str(path.relative_to(base))
  except ValueError:relative='workspace/'+path.name
  notices.setdefault(digest,{'text':text,'uses':[]})['uses'].append(f"{p['name']} {p['version']} — {relative}")
  files.append(dict(path=relative,sha256=digest))
 record=dict(name=p['name'],version=p['version'],license=p.get('license'),repository=p.get('repository'),source=p.get('source'),files=files)
 if not files:no_files.append(f"{p['name']} {p['version']}")
 inventory.append(record)
(out/'cargo-license-inventory.json').write_text(json.dumps({'upstream_commit':'970111f6cb62cc02fe36a82ea7d71b37a2889c97','target':'riscv64gc-unknown-linux-gnu','scope':'CLI normal and build dependencies, conservatively includes build-time code; excludes dev-only dependencies','packages':inventory,'packages_without_packaged_license_files':no_files},indent=2)+'\n')
with (out/'ORIGINAL-LICENSE-TEXTS.txt').open('w') as f:
 f.write('Original license/notice files from pinned Cargo sources. Identical files are deduplicated by SHA256.\nSee THIRD-PARTY-NOTICES.html and reviewed supplements for crates whose archives omit license files.\n\n')
 for digest,item in sorted(notices.items()):
  f.write('='*78+'\nSHA256: '+digest+'\nUsed by:\n'+'\n'.join(sorted(set(item['uses'])))+'\n'+'-'*78+'\n'+item['text']+'\n\n')
print(f'Inventoried {len(inventory)} packages; preserved {len(notices)} distinct original license files; {len(no_files)} archives omit separate license files.')
if no_files:print('Packages needing generated/reviewed license text: '+', '.join(no_files))
if not args.harvest_only:
 version=subprocess.check_output(['cargo','about','--version'],text=True).strip()
 if version!='cargo-about 0.9.2':raise RuntimeError(f'Required cargo-about 0.9.2; found {version}')
 subprocess.run(['cargo','about','generate','--locked','--fail','--manifest-path',str(src/'cli/Cargo.toml'),'--config',str(out/'about.toml'),'--output-file',str(out/'THIRD-PARTY-NOTICES.html'),str(out/'about.hbs')],cwd=src,check=True)
