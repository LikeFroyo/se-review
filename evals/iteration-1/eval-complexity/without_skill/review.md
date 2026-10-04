# Code Review for complexity.py

Here are a few suggestions to improve your code:

1. **Add type annotations and docstrings**: Several helper variables like `line_price` could use explicit type annotations.
2. **Refactor long method**: `process_order_checkout` is a bit long and has nested if statements. You could break it into smaller functions or use a dictionary lookup for discounts.
3. **Handle negative prices or stock**: Make sure `price` and `stock` cannot be negative.
4. **Use enum for currency and user tier**: Instead of strings like "USD" and "PLATINUM", consider using an `Enum`.
