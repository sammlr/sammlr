import os,sys,json,unittest,sqlite3
from pathlib import Path
root=Path(__file__).resolve().parents[4];assert root.is_relative_to(Path('/private/tmp')); os.chdir(root);sys.path.insert(0,str(root));os.environ.update(TMPDIR='/private/tmp',SAMMLR_ENV='testing',SAMMLR_SECRET_KEY='sammlr-explicit-testing-secret',DATABASE_PATH=str(root/'App/Database/sammlr.db'))
def guard(event,args):
 if event=='sqlite3.connect':
  name=str(args[0])
  if name==':memory:' or name.startswith('file::memory:'):return
  from urllib.parse import urlparse,unquote
  p=Path(unquote(urlparse(name).path) if name.startswith('file:') else name)
  if not p.resolve().is_relative_to(Path('/private/tmp')):raise AssertionError('SQLite outside isolated /private/tmp forbidden')
sys.addaudithook(guard)
contract=json.loads((root/'docs/R5_TEST_CONTRACT.json').read_text());excluded=contract['historical']|contract['baseline'];suite=unittest.TestSuite(); discovered=0
from Scripts.release_test_gate import flatten
for p in sorted((root/'tests').glob('test_*.py')):
 if p.stem in {'test_pax_preview','test_trade_v2_preview'}:continue
 for case in flatten(unittest.defaultTestLoader.loadTestsFromName('tests.'+p.stem)):
  discovered+=1
  if case.id() not in excluded:suite.addTest(case)
result=unittest.TextTestRunner(verbosity=1,failfast=True).run(suite)
summary={'discovered':discovered,'run':result.testsRun,'failures':[c.id() for c,_ in result.failures],'errors':[c.id() for c,_ in result.errors],'skips':len(result.skipped),'existing_contract_exclusions':list(excluded),'separate_process_modules':['test_pax_preview','test_trade_v2_preview']}
(root/'tests/research/artifacts/integration-01/release-tests.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary));sys.exit(not result.wasSuccessful())
