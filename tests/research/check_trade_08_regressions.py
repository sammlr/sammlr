"""TRADE-01–07 gates with only explicitly superseded UI expectations updated."""
import importlib.util
from pathlib import Path
BASE=Path(__file__).parent
OUT=BASE/'artifacts/trade-08'
for number in range(1,8):
    name=f'check_trade_0{number}'
    spec=importlib.util.spec_from_file_location(name,BASE/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=OUT/f'regression-0{number}';module.main()
    if number>=4:
        gallery=module.OUT/'index.html';text=gallery.read_text()
        for n in range(1,number):text=text.replace(f'href="regression-0{n}/index.html"',f'href="../regression-0{n}/index.html"')
        gallery.write_text(text)
