# Choosing a research strategy

These are design options, not an instruction to start parallel workers or spend
additional compute. Use the existing runtime and user budget.

| Situation | Useful method | Evidence that changes the next decision |
|---|---|---|
| Unknown feasibility | Small counterexample search or minimal prototype | Falsified premise, failing invariant, valid starting artifact |
| Reliable executable evaluator | Sequential proposal/evaluation/selection | Valid candidate and same-context metric improvement |
| Several distinct plausible mechanisms | Bounded independent starts | Which mechanism survives cheap evaluation; retain lineage |
| Plateau with related near misses | Recombine mechanisms; change representation | Controlled ablation against each parent |
| Expensive evaluation | Cheap rejection gates before full evaluation | Gate recall on known valid candidates; full verifier still decides |
| Noisy outcomes | Matched repeated trials and held-out confirmation | Sample distribution and uncertainty, including failures |
| Long proof or semantic gap | Decompose into lemmas; independent statement review | Exact quantifiers, assumptions and artifact linkage |

Keep an idea queue with `hypothesis`, `source`, `parent`, `expected effect`,
`cost`, `rejection criterion`, and `status`. Select by expected information and
improvement per unit of scarce resource; numerical priority formulas are optional.
If many expensive experiments share an untested assumption, test it first.

Choose breadth when uncertainty is about mechanisms and depth when a mechanism
has reproducible gains. A multistart result must count the budget of all starts,
including failures. Freeze the evaluation contract before comparing strategies.

Research journal entries should distinguish observations, deductions and
conjectures. A finite obstruction only rejects the tested construction class.
A successful local rewrite does not establish a global theorem. Literature
novelty requires a scoped, dated search and should be reported as provisional.

For stochastic tasks, do not pick the largest observed mean and declare a win.
Record all attempts, task/seed pairing, sampling plan and stopping rule. Inspect
per-task regressions, apply an appropriate interval/test for the design, and
confirm on held-out data. The bundled controller deliberately does not choose a
universal noise model or conflate sample means with lower confidence bounds.

For harness evaluation, hold model, task distribution, allowed tools and resource
accounting fixed. Compare a baseline to one mechanism at a time, then evaluate
combinations. Useful outputs are quality-versus-cost trajectories, failure rates,
time to first valid result, and robustness across problems, not only best score.

Foundations: [FunSearch](https://doi.org/10.1038/s41586-023-06924-6),
[AlphaEvolve](https://arxiv.org/abs/2506.13131),
[AI Scientist-v2](https://pub.sakana.ai/ai-scientist-v2/paper/paper.pdf),
[RE-Bench](https://metr.org/blog/2024-11-22-evaluating-r-d-capabilities-of-llms/).
The architecture here is our synthesis; these references do not validate this
implementation or establish that one strategy is universally superior.
