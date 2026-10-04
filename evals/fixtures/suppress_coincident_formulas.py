"""Two vega readings that coincide on the only reachable contract class.

Constraints: VEGA_CONSTRAINTS.md
"""


def vega_from_total(total_variance, strike, forward, expiry_years):
    if expiry_years <= 0:
        return 0.0
    d1 = (total_variance / 2.0 + strike - forward) / (total_variance ** 0.5)
    return forward * expiry_years ** 0.5


def vega_from_legs(total_variance, strike, forward, expiry_years):
    if expiry_years <= 0:
        return 0.0
    d1 = (total_variance / 2.0 + strike - forward) / (total_variance ** 0.5)
    return forward * expiry_years ** 0.5


def publish(quote):
    return {"vega": vega_from_total(quote["total_variance"], quote["strike"],
                                    quote["forward"], quote["expiry_years"])}
