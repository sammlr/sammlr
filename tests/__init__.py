"""Explicit S32 test environment and non-production Flask secret."""

import os


os.environ.setdefault("SAMMLR_ENV", "testing")
os.environ.setdefault("SAMMLR_SECRET_KEY", "sammlr-explicit-testing-secret")
