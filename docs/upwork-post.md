# Upwork portfolio item

**Title:** Landed Cost Dashboard You Can Talk To, with Numbers the AI
Cannot Invent

**Role:** Data analyst and Python developer

**Skills:** Python, FastAPI, Data Analysis, Data Visualization, LLM,
Docker, Playwright

**Media:** `view-invoices.png`, `view-anomalies.png`, `view-finance.png`,
`view-about.png`

**Description:**

An importer's cost department had to know what every part cost to land
at the plant, and answer management the day they asked. This is the
dashboard that answers, with an assistant beside it.

The AI never produces a number. It reads the question and names which
panels answer it. Python computes every figure from the invoice data.
Only then does the AI see those figures, to write one sentence around
them, and code checks every number in that sentence before it reaches
the screen. A test feeds the model wrong figures on purpose; the answer
still comes back with the right ones.

Three views on one layout, over a real run of 1,003 invoices read from
PDFs between January and October:

- **Invoices**: what came in this week, what the reader closed on its
  own, which issuer sent the most, which 22 documents a person still
  has to read. Every row opens the original PDF.
- **Anomalies**: 786 invoices scored by a checking model, 163 flagged,
  5,905,553.98 between them, each one confirmed, dismissed or still
  open.
- **Finance**: 26,483,864.42 landed over ten months, final apart from
  provisional, by part, by shipment, by component and by operation.

Built with:

- Four or five one-click questions per view that work with no AI key at
  all
- An honest refusal: when the model is down the page says so, instead
  of pretending the question was the problem
- 370 automated tests, 50 of them driving a real browser to check
  colour, layout and that no figure is ever cut off
- Docker deploy, one command

Built for finance and logistics teams that need answers they can trust
and trace back to the source document.
