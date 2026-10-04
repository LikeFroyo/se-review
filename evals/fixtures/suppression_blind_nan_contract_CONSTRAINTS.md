# Quote constraints

**C1 (binding).** A quantity that cannot be computed is NaN, never 0. A quantity absent
*by design* — a role this venue's space does not carry — is reported as a flag, never as
a NaN and never as a 0.
**Why:** 0 is a legal price on some instruments and a legal ratio on all of them, so a
substituted 0 is indistinguishable from a real observation.
