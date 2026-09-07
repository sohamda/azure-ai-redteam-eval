"""Continuous Evaluation (CE) — the hero concept.

Every code change and every deployment is automatically evaluated
for AI quality before reaching users.
"""

import os

# The vendored promptflow batch engine in azure-ai-evaluation bakes each logger's level from
# PF_LOGGING_LEVEL at import time. Set it before any CE module imports the SDK so the per-line
# progress spam ("Finished X / N lines") is suppressed. An explicit env value is respected.
os.environ.setdefault("PF_LOGGING_LEVEL", "WARNING")
