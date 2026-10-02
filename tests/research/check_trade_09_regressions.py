"""Run historical TRADE gates without replacing historical evidence."""
import importlib.util
from pathlib import Path
BASE = Path(__file__).parent
OUT = BASE / 'artifacts/trade-09'
for number in range(1, 9):
    name = f'check_trade_0{number}'
    spec = importlib.util.spec_from_file_location(name, BASE / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = OUT / f'regression-0{number}'
    module.main()
    if number >= 4:
        gallery = module.OUT / 'index.html'
        html = gallery.read_text()
        for previous in range(1, number):
            html = html.replace(f'href="regression-0{previous}/index.html"', f'href="../regression-0{previous}/index.html"')
        gallery.write_text(html)
