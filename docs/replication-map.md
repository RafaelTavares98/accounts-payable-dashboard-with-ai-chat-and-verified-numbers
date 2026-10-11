# How to replicate it

Each behavior above, turned into what the code must do. No code is
written here. This is the map the prototype will follow.

## Passo 0: the repositories that already show it

Before anything is built, read the public repositories that show the
behavior, whole or in part. They are listed and ranked in
[the reference repositories](reference-repositories.md). Two pieces
appear in no public repository: the animated connecting lines, and the
suggestion chips opening panels over the base dashboard. Those two are
ours.

## Behavior by behavior

| Behavior | What the code must do |
|---|---|
| Dashboard opens | One page renders the filtered rows as the base view |
| Chat button | One button opens a side panel with a message list |
| Suggestion chips | A fixed list of questions, one chip each |
| Answer sentence | The model writes one sentence around numbers code computed |
| Lines connect | An overlay draws a path from the answer to each new panel |
| Panels on top | Each panel is a small chart card, positioned over the base view |
| Repeat per question | Each question maps to a panel recipe, not to new code |

## The pipeline of one question

1. A person sends a question, typed or clicked.
2. The model answers with a small JSON, nothing else. That JSON names
   the panels to open and the numbers each panel must show.
3. Code reads that JSON and computes every number over the filtered
   rows.
4. Code draws the panels and the connecting lines.
5. Code passes the numbers back to the model for the final sentence.

The model never touches a row of data. It names what to show. Code shows
it. That is the rule from
[the reference](reference-behavior.md#what-the-author-says-matters-most).

## Each piece

### The dashboard

One page, one data table in memory. Every filter and every view is a
query over that table. The same rule as the reference: "cálculo direto
sobre os dados filtrados".

### The chat

A panel on one side. The history scrolls. Each answer stays visible, and
each answer keeps a button that opens its panels again.

### The suggestion chips

Written by hand, not by the model. Ten or so questions that the data can
answer. A chip is one click, which makes the demo repeatable.

### The model step

DeepSeek returns JSON with two jobs: a list of panels, and the numbers
each panel needs. The JSON output mode is described in
[the stack](stack-decisions.md#the-model). The request carries the
schema of every panel, so the model chooses from a fixed menu. It cannot
invent a panel.

### The numbers

One function per panel. Each function takes the filtered rows and
returns the number. A test fails when a figure in an answer cannot come
back out of its function.

### The refusal

Two cases, copied from the project rule:

- The question needs a column the data does not have. The answer says
  so. Nothing is invented.
- The current filter leaves too few rows. The answer says so.

### The lines

The page draws one SVG layer above everything. A line from the answer to
each panel is a path on that layer. The animation is the line drawing
itself: the visible part of the path grows from zero to full length.
The same trick exists in every chart library.

### The glass look

Three CSS pieces on each panel: a translucent background, a blur behind
it, and a light border. On the web this is called glassmorphism, and it
is three lines of style per panel.

### The data

Invented rows, never real invoices. A generator builds 15,000 rows with
a known answer, so every demo number can be checked. The same rule as
every other project in this portfolio.

## Repositories read for shape

- `vanna-ai/vanna`, 23.8k stars. Turns a question into SQL against a
  schema. Proves the shape: the model picks, the code runs.
- `shivamshayar/DB-AI`. Turns a question into charts over a local
  database. The closest public version of the reference.
- The reference itself. It is a personal post, not a repository. Its
  page in the wiki is
  [the payables panel](../../../../04-applications/project-12-payables-panel.md).

## What is still open

Which subject the data has. The reference uses accounts payable, which
is Rafael's own area. The page in the wiki asks the same question, and
it stays open until he decides.
