# Parameter lists — flags, arity, and parameter objects

Audit function signatures and argument passing.

## What to look for

- **Boolean flag parameters:** Passing boolean flags (`is_vip`, `apply_discount`, `send_email`) that branch internal behavior (split into two distinct functions or pass a strategy/enum instead).
- **Excessive parameter arity:** Functions requiring >3–4 positional parameters without grouping them into a typed parameter object or struct.
- **Output parameters:** Mutating arguments passed by reference instead of returning structured return values.
- **Optional parameter explosion:** Long chains of `None`/`null` default parameters suggesting multiple responsibilities in one procedure.
- **Adjacent parameters of the same type:** A signature with two or more same-typed parameters next to each other — two coordinates, a start and an end, a key and a value, a lower and an upper bound — where the call site can transpose them with no type error and no name to catch it.
