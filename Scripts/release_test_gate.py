"""Run explicit release, historical archive, or baseline cohorts in a clean candidate."""

import argparse
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=('release', 'historical', 'baseline'), required=True)
    args = parser.parse_args()
    if not ROOT.is_relative_to(Path('/private/tmp')):
        raise RuntimeError('Tests must run inside an isolated /private/tmp candidate')
    os.environ['SAMMLR_ENV'] = 'testing'
    # The existing tests package establishes the explicitly synthetic test secret.
    import tests  # noqa: F401

    contract = json.loads((ROOT / 'docs/R5_TEST_CONTRACT.json').read_text())
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), top_level_dir=str(ROOT))
    cases = {case.id(): case for case in flatten(suite)}
    exclusions = contract['historical'] | contract['baseline']
    unknown = set(exclusions) - set(cases)
    if unknown:
        raise RuntimeError(f'Stale cohort entries: {sorted(unknown)}')
    for record in exclusions.values():
        if not record['reason']:
            raise RuntimeError('Every non-release test needs an explicit classification')
        for replacement in record.get('release_contracts', []):
            if replacement not in cases or replacement in exclusions:
                raise RuntimeError(f'Missing release protection: {replacement}')
    selected = [case for name, case in cases.items() if (
        name not in exclusions if args.cohort == 'release'
        else name in contract[args.cohort]
    )]
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
    print(json.dumps({
        'cohort': args.cohort, 'discovered': len(cases), 'run': result.testsRun,
        'failures': len(result.failures), 'errors': len(result.errors),
        'skipped': len(result.skipped),
        'historical_classified': len(contract['historical']),
        'baseline_classified': len(contract['baseline']),
        'failed_ids': [case.id() for case, _ in result.failures + result.errors],
    }, sort_keys=True))
    # No expectedFailure/skip masking: every executed failure remains a failure.
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == '__main__':
    raise SystemExit(main())
