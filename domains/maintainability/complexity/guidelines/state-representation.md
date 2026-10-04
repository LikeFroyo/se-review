# State representation — modelling states that cannot all happen

Audit how a lifecycle is represented. The question is not how many fields the record has; it is whether an invalid combination is representable at all.

## Boolean state

- **Independent booleans instead of a lifecycle:** `is_paid`, `is_cancelled`, `is_refunded` as separate fields, so `paid ∧ cancelled ∧ refunded` is a perfectly storable record and no assignment can reject it.
- **No invariant enforced at the transition:** A method that flips one flag without checking the others, so a terminal state can be left or a forbidden transition taken with no error.
- **Terminal state is not absorbing:** A cancelled or settled record that can be modified again, because nothing in the type or the code refuses the write.
- **Flags as a substitute for a state machine:** A growing set of booleans whose combination is meant to be interpreted, where the interpretation logic is duplicated in every branch that reads them.

## Absent states

- **State encoded by field presence:** A record whose status is inferred from which optional fields are set, so a partially written record reads as a valid later state.
- **Status as an unvalidated string or int:** A status field with no closed set at the type or schema boundary, so an unrecognised value falls through to a default branch.
- **State split across records:** A lifecycle whose stages live in separate rows or collections with no single authority, so the overall state has no single definition.
