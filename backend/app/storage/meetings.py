"""
In-memory meeting registry

KEY   → meeting_id
VALUE → meeting payload (dict)
"""

MEETINGS: dict[str, dict] = {}
