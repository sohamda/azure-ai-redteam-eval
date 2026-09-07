"""Red Teaming — adversarial evaluation (part of Continuous Evaluation).

Stress-tests the AI system with prompt injection, jailbreak,
PII extraction, and harmful content probes.
"""

import os

# Suppress the vendored promptflow batch-engine progress spam before azure-ai-evaluation is
# imported (its loggers bake in PF_LOGGING_LEVEL at import time). An explicit env value is respected.
os.environ.setdefault("PF_LOGGING_LEVEL", "WARNING")
