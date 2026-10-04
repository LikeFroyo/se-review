# Cold start and reset — behaviour before there is anything to observe

Audit what the system does when its accumulated state is empty, absent, or freshly rebuilt. These
paths are the least exercised in normal operation and the most consequential when they are wrong.

## Cold start

- **Undefined at low sample counts:** A statistic, ratio, or decision has no defined behaviour for zero or very few observations — dividing by a count, a variance at n=1, a threshold crossed on noise in the first seconds of life.
- **Empty store treated as failure:** An absent or empty store is handled as an error where the correct behaviour is to start clean, so a first run fails where every later run succeeds.
- **Warm and cold paths differ silently:** Two code paths serve the same question depending on whether state exists, and only one is exercised by the checks.

## Reset and recovery

- **Continuity assumed across restart:** A counter, sequence, or identity that a peer or an accounting total assumes is continuous is silently restarted, so the two disagree from the restart onward.
- **Resume with no compatibility check:** Persisted state is reloaded with no version, format, or poison check, so an incompatible snapshot is accepted as valid.
- **No stated answer to what resets:** Nothing declares which state is held between calls, which a fresh start rebuilds, and which it carries over — so the answer is whatever the code happens to do.
