# Conversion — scaling a value, and paying for it twice

Audit every scale change, and every chain of them.

## What to look for

- **Conversion factor applied to the wrong side:** A multiply where a divide was needed, or a divide where a multiply was needed, on a value whose magnitude is fixed by an interface contract.
- **Conversion applied twice:** A producer converting to a base unit and a consumer converting again from base, so the value is scaled twice and the two disagree by a square of the factor.
- **Conversion applied in neither:** A value in a smaller unit consumed as if it were in a larger one, which is the same defect as a wrong factor with the same blast radius.
- **Cumulative rounding across a chain:** A value converted and rounded at each hop, so a total assembled from many converted components does not equal the conversion of the total.
- **Unit carried in the name only:** The unit known only from a field or variable name, so a caller passing the value in a different unit compiles, runs, and is silently wrong.
- **Mixed-unit aggregation:** Values in different units summed or averaged together in one expression, so the result is not a quantity at all.
- **Scaling on the storage boundary only:** A value stored in a scaled form and returned in the same form, so a second consumer applies the inverse it was never told about.
- **Precision lost on a widening or narrowing:** A conversion that fits in the source type but exceeds the destination's declared precision, so the value is rounded with no indication to the consumer.
