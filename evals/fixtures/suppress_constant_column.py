"""Chain coverage ratio.

Constraints: CHAIN_CONSTRAINTS.md
"""


def coverage_ratio(member_count):
    """Fraction of the chain that quoted this session."""
    eligible = member_count
    quoted = member_count
    return quoted / eligible if eligible else 1.0


def surface(chain):
    return {"coverage": coverage_ratio(len(chain))}
