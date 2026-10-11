# The reference behavior

The reference is a dashboard video Rafael sent, `MUST REPLICATE NOW.mp4`,
plus the author's own description in `MUST REPLICATE.txt`. The images he
sent could not be read, so this page comes from the text file and from his
spoken description of what happens on screen.

## What the author built

- One panel over 15,000 accounts-payable rows, 2024 to 2027.
- Filters for category, cost centre, status, branch and period.
- Four views in a left rail.
- One button, "Perguntar aos dados".
- A local model, Phi-3.5, running inside the browser over WebGPU.
- No call to any external service.

## The behavior, in the order it happens

1. **The dashboard opens.** The base view shows the accounts-payable
   numbers for the current filters.
2. **He clicks the chat button.** A chat panel appears.
3. **The chat offers ready answers.** A few suggestion chips wait there.
   He does not type. He clicks one.
4. **The answer arrives as a sentence.** It names the number and the
   slice of data it used.
5. **Lines are drawn.** Animated lines connect the clicked answer to new
   panels.
6. **New panels open on top of the base dashboard.** Each panel shows the
   same analysis through another dimension: by month, by category, by
   supplier, by cost centre.
7. **The loop repeats.** Each new question opens the panel type that fits
   that question. A question about totals gets one set. A question about
   overdue accounts gets another.

## The look

The panels sit over the dashboard like sheets of blue glass. The lines
animate as they connect the answer to the panels. The whole thing feels
like one surface, not separate windows.

## What the author says matters most

- The assistant identifies what must be shown: it switches the view,
  draws charts, and shows only the analysis that relates to the question.
- The numbers are computed directly over the filtered data.
- The model only reads the question and chooses what to show.

## What changes here

The reference runs Phi-3.5 locally in the browser. This project calls the
DeepSeek V4 API instead. That trade is described in
[the stack](stack-decisions.md#the-model).
