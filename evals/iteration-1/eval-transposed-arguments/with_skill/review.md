Reviewing your transposed-arguments fixture — inspecting the file and run directory.
Got the fixture — now gathering review context.
Mapped the scoring rubric — now loading the evaluation domains.
Initial domain scan points to contract and clarity risks — now verifying with execution.
# Review: `evals/fixtures/transposed_arguments.py` (focused single-file)

`6 findings · C:0 M:3 m:3 i:0 · Mean 93.5/100 · Final Grade C`
Covered: 1/1 files · Scope: focused on: `evals/fixtures/transposed_arguments.py` · Not examined: 0 — none
Paths: 0 · Unmapped: 0 — no entry points; pure in-process helpers with no I/O, parsing, or trust crossing
Unclassified: 0 findings fit no axis code
Domain Scores: Correctness: 77/100 · Maintainability: 87/100 · Leanness: 97/100 · Security: 100/100 · Operations: 100/100 · Interoperability: 100/100
Gated by: weakest domain: correctness (C) — **always printed.**

## Findings

### [MAJOR] `set_viewport` stores `top` as `PLOT_BOTTOM`, drops `right`/`bottom`
- **Domain:** Correctness (A1)
- **Verified by:** RAN — imported module, called `set_viewport(10,20,30,40)`, observed `PLOT_LEFT==10, PLOT_BOTTOM==20` instead of `BOTTOM==40`
- **Evidence:** `transposed_arguments.py:27-31` — `def set_viewport(left: int, top: int, right: int, bottom: int)` then `PLOT_LEFT = left; PLOT_BOTTOM = top`
- **Failure scenario:** Every subsequent `plot_series` render is offset vertically by `top - bottom` pixels; viewport can never be set correctly. `right` is accepted and silently ignored, so a caller narrowing the right edge sees no effect.
- **Fix:** Assign the correct names, scope: local — `PLOT_BOTTOM = bottom`, use or remove `right` (e.g. store `PLOT_RIGHT` or drop the parameter as a boundary change).
- **Trade-off:** Local one-line fix; cost is deciding the `right` contract (store vs. remove changes the signature — boundary scope if removed).

### [MAJOR] Adjacent same-type parameters invite silent transposition
- **Domain:** Maintainability (B1)
- **Verified by:** DERIVED — chain: `plot_series(points, width, height)` + `points: list[tuple[int,int]]` + `set_viewport(left, top, right, bottom)` + `clamp(value, lo, hi)`; all adjacent `int` pairs with no keyword-enforcement, nominal typing, or newtype to catch a swap
- **Evidence:** `transposed_arguments.py:13` (`width: int, height: int`), `transposed_arguments.py:27` (four `int`s), `transposed_arguments.py:34` (`lo: int, hi: int`), plus `tuple[int,int]` points noted in `transposed_arguments.py:14-20` docstring
- **Failure scenario:** `plot_series(pts, h, w)` builds a `w×h` grid transposed — either `IndexError` or a chart mirrored about the diagonal; `set_viewport(l, b, r, t)` compiles and silently misplaces the origin; `clamp(v, hi, lo)` returns a wrong bound (RAN: `clamp(5,10,0)==10`, not `5`). The file's own comments admit callers "routinely" do this.
- **Fix:** Boundary scope — make transposition unrepresentable: keyword-only args, `Viewport`/`Bounds(lo,hi)`/`Size(w,h)` value objects, or `NewType` wrappers for X vs Y. At minimum enforce keyword calls at the three call sites.
- **Trade-off:** Adds one small type per concept and migrates callers; cost is proportional to caller count (here: the fixture only), plus slightly more verbose call sites.

### [MAJOR] `clamp` accepts inverted bounds and returns an out-of-range value
- **Domain:** Correctness (A8)
- **Verified by:** RAN — `clamp(5,0,10)==5` correct; `clamp(5,10,0)==10`, i.e. `max(10, min(0,5))`, outside the intended `[0,10]`
- **Evidence:** `transposed_arguments.py:34-36` — `return max(lo, min(hi, value))` with no `lo <= hi` guard, documented as "callers routinely pass (hi, lo)"
- **Failure scenario:** Any transposed call silently clamps to the wrong edge, propagating a wrong limit into viewport/grid math instead of failing fast.
- **Fix:** Module scope — normalize (`if lo > hi: swap` or `raise ValueError`) in `clamp`, so all callers share one contract; documented is not resolved, so the comment alone does not fix it.
- **Trade-off:** `raise` surfaces caller bugs but adds exception handling at call sites; swap is silent-tolerant but hides the transposition — prefer `raise` for new code, swap only for back-compat.

### [MINOR] `plot_series` reads ambient viewport globals instead of parameters
- **Domain:** Maintainability (B2)
- **Verified by:** READ
- **Evidence:** `transposed_arguments.py:21-24` — `grid[PLOT_BOTTOM + y][PLOT_LEFT + x] = 1` reads module globals mutated by `set_viewport`
- **Fix:** Pass the origin/viewport explicitly or encapsulate grid + origin in one object.

### [MINOR] Unused surface: `LINE_SPACING` and `set_viewport(right)`
- **Domain:** Leanness (L2)
- **Verified by:** DERIVED — repo-wide search for `LINE_SPACING` finds only the definition at `transposed_arguments.py:6`; `right` at `transposed_arguments.py:27` is never read in `transposed_arguments.py:29-31`
- **Evidence:** `transposed_arguments.py:6` (`LINE_SPACING = 8`, never referenced); `transposed_arguments.py:27-31` (`right` parameter, no use)
- **Fix:** Deletion — remove `LINE_SPACING` or wire it in; remove or implement `right`.

### [MINOR] `plot_series` has no bounds check on points
- **Domain:** Correctness (A1)
- **Verified by:** READ
- **Evidence:** `transposed_arguments.py:22-23` — direct `grid[PLOT_BOTTOM + y][PLOT_LEFT + x] = 1` with caller-controlled `x, y`, `width`, `height`
- **Fix:** Localized cleanup — clip, skip, or raise on out-of-range points; document the chosen contract.

## Aligns well
- `clamp` core expression `max(lo, min(hi, value))` is the correct idiom for the non-transposed case (A1)
- Type annotations on all three signatures state intent explicitly (A8)
- Module docstring honestly flags the transposition hazard instead of hiding it — the flag is correct, only the enforcement is missing (B4)

Ruling: code-is-right for `plot_series` inner indexing given correct inputs; doc-as-intent for `set_viewport` (parameter names state the contract the body violates).