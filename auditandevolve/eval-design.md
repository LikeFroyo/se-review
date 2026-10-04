# Eval design (precondition for Phase 4)

An eval must satisfy four properties before it can measure anything. A corpus missing
any of them produces confident nonsense rather than a weak signal, so this is a
precondition on Phase 4, not advice inside it.

Run `python scripts/eval_diagnostics.py` for the mechanical checks below.
Run `python scripts/eval_diagnostics.py --determinism N` before trusting any delta.

## Sampling order (mirror production, then harden)

Sample inputs in this order, per the upstream guidance catalogued in `SOURCES.md`:

1. Production transcripts (ask about retention and sensitive data first).
2. Bug reports and support tickets.
3. Five to ten cases written by hand.
4. Cases synthesized from the codebase, anchored in real examples.

Show every input for human approval before grading begins. Include
should-not-fire cases. Be able to say why each hard case is hard before
adding it.

## The four properties

1. **Tasks mirror production.** Sample the tasks you actually care about, not the ones
   that are easiest to generate or grade. A distribution chosen for convenience measures
   the convenience.
2. **Performance improves with stronger models and more thinking.** If a more capable
   model at higher effort does not score higher, the tasks are ambiguous or the grader
   is miscalibrated. Do not tune the skill against a broken measuring instrument.
3. **Passable headroom at the frontier.** The most capable model at highest effort must
   sit well below 100%, or changes cannot be judged. The gap must not be made of
   impossible or ambiguous tasks. Two tells:
   - a task that fails *every* run, regardless of replicates — a broken task, not a hard one;
   - a task where two domain experts would not reach the same verdict, or where the
     grader checks something the task never stated.
   A good task is one where two experts agree and everything the grader checks is
   discoverable from the task.
4. **Low run-to-run variance.** Variance comes from ambiguous tasks, from a grader that
   returns different verdicts on identical output, from inconsistent configuration such
   as effort not applied uniformly, and from the environment — leftover files or git
   history can hand the agent the answer.

## Adversarial sampling

Model capability is jagged. Selecting cases because *today's model* fails them samples
the valleys of one model's capability surface. The corpus becomes that model's failure
fingerprint, and stops measuring what is intrinsically hard or valuable.

Include a case because a human judged it hard, and be able to say why before adding it.
Specific failures observed in production traffic, bug reports, and tickets are the best
source. Do not sample traffic alone: users often attempt what they expect to work, so a
distribution drawn strictly from user traffic skews easy.

## Choosing and validating the grader

Pick the cheapest grader the output shape allows.

- **Constrained output → programmatic.** Exact match, a label from a fixed set,
  schema-valid JSON, or tests that pass.
- **Open-ended output with clear quality criteria → LLM judge.** Write the rubric as
  checkable claims, never a 1-to-5 scale. When a baseline exists, judge pairwise instead:
  read both outputs in random order, without being told which is the baseline, and pick
  the better one.
- **The judge must not be the model under test.**

Then validate it: grade a handful of cases and ask whether you would have scored any of
them differently. Read a sample of scored transcripts before believing the evaluator.
Scoring failures are among the most common ways an eval is misconfigured, and they are
invisible in the aggregate score.

## Diagnostics

`scripts/eval_diagnostics.py` reports all four. Treat any of them as blocking.

- **Headroom** — the with_skill pass rate. At or above 95% the corpus is saturated: every
  future change is inside the noise, and quality hillclimbing cannot work. Switch the
  objective to latency, which is measurable, rather than pretending to improve quality.
  Cost is **not** an available substitute: see `hillclimb.md § What each objective can
  actually be measured by` for why this harness cannot measure it.
- **Trigger rate** — the fraction of rollouts that actually opened the skill, measured
  from tool calls. Whether the prompt *mentioned* the skill is not evidence it was used.
- **Grader determinism** — grade one stored review twice and report the flip rate. A
  grader that changes its verdict on identical output puts every score inside the noise
  it creates. Pass `--determinism N` to sample N stored reviews.
- **Plumbing** — timeouts, API errors, denied tools, and cut-off answers are
  infrastructure noise, not model variance. `scripts/run_evals.py` refuses to grade
  runs without a review body and writes `plumbing.json`; diagnostics excludes those
  runs from task tells.

**Repeats are supported; using them is not optional.**
`scripts/run_evals.py --reps N` runs an eval N times in a fresh workspace each time and records
every replicate with a within-eval standard deviation, which `eval_diagnostics.py` prints as
`REPLICATE SPREAD`. That spread is the noise floor Phase 5 requires before round one.

Until an eval has been run with `--reps 2` or more it has no noise floor, so:

- quote any delta on it as a point estimate and say the interval is unavailable;
- **do not start a Phase 5 round on it.** The precondition cannot be met by intention.

`grade_evals.py` prints an across-eval standard deviation beside the headline. That is
dispersion between different evals, not run-to-run variance, and it is never a noise floor.

## A broken task is not a model failure

When a task fails every run, or its assertions cannot be satisfied by a competent
reviewer, the defect is in the task or the grader. Fix the task. Do not weaken the
reviewer, and do not relax an assertion until a wrong review passes — that converts a
detectable defect into an undetectable one, and inverts the eval: the corpus starts
rewarding the behaviour the skill exists to suppress.