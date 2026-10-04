"""Set-level view over per-contract facts.

Constraints: SET_CONTRACT_CONSTRAINTS.md
"""
from per_contract_layer import parity_fit_impl


def set_view(contracts):
    fit = parity_fit_impl([c.close for c in contracts])
    return {"forward": fit["forward"], "width": fit["width"]}
