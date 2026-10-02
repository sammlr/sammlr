"""Bootstrap the explicit testing secret for plain unittest discovery.

The S35 gate is intentionally executable exactly as documented. Production
and development imports do not load this test-only module.
"""

import os
import unittest


os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")


class S35GateEnvironmentTestCase(unittest.TestCase):
    def test_plain_discovery_uses_the_explicit_s32_testing_secret(self):
        self.assertEqual("testing", os.environ["SAMMLR_ENV"])
        self.assertEqual(
            "sammlr-explicit-testing-secret", os.environ["SAMMLR_SECRET_KEY"]
        )
