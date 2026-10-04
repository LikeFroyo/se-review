"""The per-contract layer. Its public door is `published_names`."""


def parity_fit_impl(strikes):
    """A private helper. Reachable only through the layer's door, by design."""
    return {"forward": sum(strikes) / len(strikes), "width": max(strikes) - min(strikes)}


def smile_solve_impl(nodes):
    return {"nodes": nodes}


def log_ratio_impl(a, b):
    return a / b


published_names = ("parity_fit_impl", "smile_solve_impl", "log_ratio_impl")
