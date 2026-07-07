"""AI Budget Analyst: automated budget analysis with a Claude narration layer.

Golden rule: the LLM never does arithmetic. All figures are computed
deterministically with pandas/NumPy; Claude maps schemas, decides which
analyses matter, and writes the memo around verified numbers.
"""

__version__ = "0.1.0"
# EOF-SENTINEL
