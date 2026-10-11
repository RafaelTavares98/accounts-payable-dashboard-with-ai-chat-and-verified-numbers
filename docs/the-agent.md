# The agent

What the question-answering half is, what is wrong with it, and what a
serious version does instead.

Written 2026-10-10, after Rafael typed a question and the panel looked
dead for twenty seconds.

---

## What happens today, in order

| # | Step | Who | Cost |
|---|---|---|---|
| 1 | the question is read, panels are named | `deepseek-v4-pro` | ~9s |
| 2 | every figure is computed over the filtered rows | code | ~0s |
| 3 | the figures are handed back for a sentence | `deepseek-v4-pro` | ~11s |
| 4 | the sentence is checked for invented numbers | code | ~0s |

Two sequential calls to a large model. About twenty seconds, during
which the page shows nothing at all.

---

## The ten gaps

### Latency

**1. No pending state.** The page gives no sign that anything is
happening. Twenty seconds of silence reads as a broken button, which is
exactly what Rafael reported. This is the whole bug: the agent answered
every time.

**2. The router does not need a large model.** Step 1 picks from a menu
of seven names. That is a classification, and `deepseek-flash` costs
US$0.15 per million input tokens against `deepseek-v4-pro` at US$0.66,
and answers in a fraction of the time. Routing is the cheapest possible
job and it is being given the most expensive model.

**3. Nothing is streamed.** The sentence arrives whole. Streaming turns
eleven seconds of nothing into words appearing, which is the difference
between slow and broken.

**4. Nothing is cached.** The same question over the same filter costs
the same two calls every time. A plan is a function of the question and
the menu, not of the data, so it can be remembered. The figures must
never be cached: they are recomputed every time, which is what keeps the
answer honest.

### Reliability

**5. Bad JSON is a refusal, not a retry.** When the model answers with
prose, the whole turn is thrown away. A repair prompt that shows the
model its own bad reply and the schema again recovers most of these.

**6. The plan is barely validated.** Names are checked against the menu.
Nothing checks the shape, the count, or whether the panels make sense
together.

**7. The number guard is too literal.** It compares strings. A model
that writes `1.12M`, or `31,750` instead of `31,750.00`, is treated as
having invented a figure, and a correct sentence is thrown away. The
comparison should be on the value, not on the text.

### What it cannot do at all

**8. No memory.** "And for Marsk?" is meaningless to it. Each question
arrives alone, with no sight of the one before. The fix is to send the
previous turns' *questions and panel names* only, never the figures, so
the model still cannot do arithmetic.

**9. No evaluation.** Nobody can say whether a prompt change made the
routing better or worse. The practice here is a **golden set**: thirty
or so written questions with the panels each one should open, run
offline against a recorded model, scored as plain accuracy. Langfuse's
own guidance is 10 to 1,000 items, built from real traces, covering the
known failure modes, and versioned.

**10. No observability.** Nothing is recorded per turn: not the
latency, not the tokens, not whether the sentence was rejected. Without
it, "the agent is slow" is an anecdote.

---

## What a serious version does

| Gap | The fix |
|---|---|
| 1 | a pending bubble at once, the Send button disabled |
| 2 | `deepseek-flash` routes, `deepseek-v4-pro` narrates |
| 3 | the sentence streams |
| 4 | the plan is cached by question and menu; figures never are |
| 5 | one repair attempt on unparseable JSON |
| 6 | the plan is checked for shape and length |
| 7 | the guard compares values, not strings |
| 8 | the last few turns' questions and panels travel with the prompt |
| 9 | a golden set and an offline routing score |
| 10 | one line per turn: latency, tokens, panels, rejected or not |

---

## Where it stands

Read from the code on 2026-10-10, after the rebuild.

| Gap | State |
|---|---|
| 1 | closed: a waiting bubble, and Send is disabled |
| 2 | closed: `deepseek-flash` routes, `deepseek-v4-pro` writes |
| 3 | open: the sentence still arrives whole |
| 4 | open: no plan is cached |
| 5 | closed: one repair prompt on a reply that is not json |
| 6 | in part: three to five panels are enforced; the mix is not checked |
| 7 | in part: the guard accepts a figure with its commas removed |
| 8 | closed: the last six turns travel, text only, no figures |
| 9 | open: no golden set |
| 10 | open: nothing is recorded per turn |

The wait fell from twenty seconds to about 6.5.

---

## The rule that does not move

None of this touches the one rule. The model still never produces a
number. Caching a plan is caching a choice of panels, not a figure.
Memory carries questions and panel names, not totals. The guard gets
cleverer about reading a sentence, not more forgiving about what may be
in it.
