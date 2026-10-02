"""Historical TRADE gates, new evidence only."""
import importlib.util
import os
from pathlib import Path
BASE=Path(__file__).parent
OUT=BASE/'artifacts/trade-10'
for number in range(int(os.environ.get('TRADE_REGRESSION_START', '1')),10):
    name=f'check_trade_{number:02}'
    spec=importlib.util.spec_from_file_location(name,BASE/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.OUT=OUT/f'regression-{number:02}';module.main()
    if number>=4:
        gallery=module.OUT/'index.html';html=gallery.read_text()
        for previous in range(1,number):
            html=html.replace(f'href="regression-{previous:02}/index.html"',f'href="../regression-{previous:02}/index.html"')
        gallery.write_text(html)
parity=BASE/'check_trade_09_parity.py'
(OUT/'regression-09-parity').mkdir(exist_ok=True)
exec(compile(parity.read_text().replace('artifacts/trade-09','artifacts/trade-10/regression-09-parity'),str(parity),'exec'),{'__file__':str(parity.resolve()),'__name__':'__main__'})
