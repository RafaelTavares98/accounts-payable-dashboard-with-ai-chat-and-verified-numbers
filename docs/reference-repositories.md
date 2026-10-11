# The reference repositories

One step of the plan: find public repositories that show the described
behavior, whole or in part. Searched on GitHub on 2026-10-10, sorted by
stars. Python and Docker come first, as Rafael decided. Other languages
stay when only they show the exact behavior.

## What each one demonstrates

| Repository | Stars | Language | Which behavior it shows |
|---|---|---|---|
| [pandas-ai](https://github.com/sinaptik-ai/pandas-ai) | 23.9k | Python | chat with CSV and SQL, natural language to analysis, docker compose |
| [vanna](https://github.com/vanna-ai/vanna) | 23.8k | Python | question to SQL against a schema, MIT |
| [Data-Analysis-Agent](https://github.com/Zafer-Liu/Data-Analysis-Agent) | 2.6k | JavaScript | chat with data, auto visualizations and insights |
| [dataline](https://github.com/RamiAwar/dataline) | 1.6k | TypeScript | chat with CSV and databases, charts, docker compose |
| [bagofwords](https://github.com/bagofwords1/bagofwords) | 459 | Python | chat with data, rules, memory, deploy in two minutes |
| [lumen](https://github.com/holoviz/lumen) | 316 | Python | natural language to SQL, charts, dashboards and reports, BSD-3 |
| [querychat](https://github.com/posit-dev/querychat) | 212 | Python | chat with data in R and Python |
| [hermes-ui](https://github.com/pyrate-llama/hermes-ui) | 199 | HTML | the glass chat panel, glassmorphism |
| [automated-data-analyst](https://github.com/saineshnakra/automated-data-analyst) | 30 | Python | chat with data, verified calculations with pandas |
| [thebingoai](https://github.com/thebingoai/thebingoai) | 11 | Python | BI platform, AI dashboards, chat, FastAPI and Nuxt |

## The reading order for the prototype

1. `thebingoai`. The closest whole shape: Python backend, chat, dashboards.
2. `automated-data-analyst`. The numbers rule: code checks every figure.
3. `bagofwords`. The chat over rows, in Python, easy to run.
4. `hermes-ui`. The glass look of the chat panel.
5. `vanna` and `pandas-ai`. How the model asks code for a result.
6. `lumen`. An agent framework that turns language into dashboards.

## What none of them shows

- The animated lines connecting an answer to the new panels. No public
  repository was found that does this. That piece stays ours.
- The suggestion chips plus panels opening over the base dashboard.
  `Data-Analysis-Agent` and `thebingoai` come closest, each in part.

The stack decision that this step closed is recorded in
[the stack](stack-decisions.md#decided).
