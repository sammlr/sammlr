import os,sys,importlib.util,json,time
from pathlib import Path
root=Path(__file__).resolve().parents[4];assert root.is_relative_to(Path('/private/tmp')); os.chdir(root);sys.path.insert(0,str(root));os.environ.update(TMPDIR='/private/tmp',SAMMLR_ENV='testing',SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',DATABASE_PATH=str(root/'App/Database/sammlr.db'))
def guard(event,args):
 if event=='sqlite3.connect':
  from urllib.parse import urlparse,unquote
  name=str(args[0]);p=Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
  if name!=':memory:' and not name.startswith('file::memory:') and not p.resolve().is_relative_to(Path('/private/tmp')):raise AssertionError('SQLite outside /private/tmp forbidden')
sys.addaudithook(guard)
results=[]
for n in range(1,12):
 name=f'check_trade_{n:02}';p=root/'tests/research'/f'{name}.py';spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.BASE='http://127.0.0.1:18095';m.OUT=root/'tests/research/artifacts/integration-01/preview'/name
 print('START',name,flush=True);m.main();results.append(name);(root/'tests/research/artifacts/integration-01/preview-regression.json').write_text(json.dumps(results));print('PASS',name,flush=True)
p=root/'tests/research/check_trade_09_parity.py';s=p.read_text();assert "BASE='http://127.0.0.1:8095'" in s
s=s.replace("BASE='http://127.0.0.1:8095'","BASE='http://127.0.0.1:18095'")
print('START canonical numeric stack parity',flush=True);exec(compile(s,str(p),'exec'),{'__file__':str(p),'__name__':'__main__'});results.append('check_trade_09_parity');(root/'tests/research/artifacts/integration-01/preview-regression.json').write_text(json.dumps(results))
