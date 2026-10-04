"""One implementation of position sizing, reached two ways.

Constraints: SIZING_CONSTRAINTS.md
"""

SIDE = {"BUY": 1, "SELL": -1}


def signed_quantity(side, quantity):
    sign = SIDE[side]
    return sign * quantity


HANDLERS = {}


def register(name, handler):
    HANDLERS[name] = handler


def size_order(order):
    return signed_quantity(order["side"], order["quantity"])


# Registered by the legacy entry point, which predates size_order and was never
# retired. It reaches the same sizing decision without applying the sign.
register("legacy", lambda order: order["quantity"])
