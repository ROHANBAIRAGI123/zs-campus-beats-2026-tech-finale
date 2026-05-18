# ZS Tech Challenge — Retail Network Intelligence

> **Superset × ZS Associates · Campus Beats 2026**
>
> Confidential — for participating teams. Released **19 May 2026**.

This repository holds the dataset, instructions, and tooling for the **Retail Network Intelligence** challenge. You will work with a relational dataset modelled on a multi-city Indian retail chain (physical stores, dark stores, online-fulfilment centres) and answer business questions across **4 parts**.

---

## TL;DR — getting started

```bash
# 1. clone
git clone <this-repo-url>
cd zs-tech-challenge

# 2. install deps (only Python stdlib needed for the downloader)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # pandas + duckdb (recommended)

# 3. download the bulk data (~2 GB compressed) from S3
python3 scripts/download_data.py

# 4. (recommended) load everything into a single DuckDB database
python3 scripts/load_into_duckdb.py
duckdb zs_challenge.duckdb
```

You're now ready to run SQL or pandas against the full dataset.

---

## What's in this repo

```
.
├── input/
│   └── zs-tech-challenge-problem-statement.md   # the problem statement
├── docs/
│   └── data_dictionary.md                       # schema reference
├── samples/
│   └── *.csv                                    # 200-row preview of every table
├── scripts/
│   ├── download_data.py                         # OS-agnostic S3 downloader
│   └── load_into_duckdb.py                      # one-liner to load CSVs into DuckDB
├── data/                                        # populated by download_data.py — gitignored
└── README.md
```

The `samples/` folder is **committed** to git so you can browse the schema without downloading anything.
The full `data/` folder is **not** in git — it lives on S3.

---

## The four parts

See [`input/zs-tech-challenge-problem-statement.md`](input/zs-tech-challenge-problem-statement.md) for the full brief.

| | Part | Theme |
|---|---|---|
| 1 | Store Performance Intelligence | Find the **3rd highest performing store** per metro region for a given super-category, in the most recent completed quarter. Bonus: revenue efficiency vs effective in-stock days. |
| 2 | Growth & Trend Analysis | **QoQ growth** of a chosen metric across the last 6 quarters per region, with event-adjusted flag. Bonus: distortion-removal logic. |
| 3 | Forward-Looking Insight | Forecast next quarter's metric per region-category. Bonus: scenario-based forecasts + top 3 drivers. |
| 4 | Retail Intelligence Copilot | **Design an AI agent** that lets business stakeholders query this dataset in natural language with grounded, cited answers. Bonus: extend it into an autonomous anomaly investigator. |

The **most recent completed quarter** as of release date (19 Mar 2026) is **2026-Q1** (Jan–Mar 2026).

---

## The dataset at a glance

13 tables, ~2 GB compressed, ~9–10 GB uncompressed.

| Table | Rows |
|---|---|
| `calendar` | ~820 |
| `categories` | ~120 |
| `stores` | 150 |
| `store_geo_mapping` | ~155 |
| `store_events` | ~50 |
| `products` | 4,000 |
| `pricing_history` | ~10,000 |
| `customers` | 400,000 |
| `promotions` | 3,000 |
| `inventory_snapshots` | ~9,000,000 |
| `orders` | ~6,000,000 |
| `order_items` | ~15,000,000 |
| `returns` | ~750,000 |

Read [`docs/data_dictionary.md`](docs/data_dictionary.md) for the schema reference before writing any SQL.

---

## Working with the data

### Option A: DuckDB (recommended, fastest)

```bash
pip install duckdb
python3 scripts/load_into_duckdb.py
duckdb zs_challenge.duckdb
```

DuckDB reads `.csv.gz` natively, runs vectorized OLAP queries, fits in a single binary, and works on every OS.

### Option B: pandas

```python
import pandas as pd
orders = pd.read_csv("data/orders.csv.gz")           # ~6M rows — works but slow
items  = pd.read_csv("data/order_items.csv.gz", chunksize=2_000_000)  # use chunking for the big one
```

### Option C: Postgres / MySQL / Spark / your stack of choice

You're free. The data is plain CSV. We provide DuckDB as a sensible default — not a requirement.

---

## Submission expectations

(See your participant brief from ZS for exact deliverables and timeline.)
At minimum, your submission should include:
- queries / notebooks / scripts producing each part's output
- a short write-up of the business logic you applied and why
- for Part 3, the forecasting method + driver analysis
- for Part 4, the agent design artefacts listed in the problem statement

---

## FAQ

**Q: The download is slow / failing.**
The downloader supports resuming (`--force` to re-download a single file) and per-table downloads (e.g. `python3 scripts/download_data.py orders order_items`). If S3 is unreachable from your network, contact the organisers for a mirror.

**Q: I think I found something inconsistent in the data.**
The dataset reflects a real operational system — verify your interpretation against the data, decide a policy, document your choice in your write-up, and move on. We are evaluating judgement, not gotcha-spotting.

---

## Authors & contact

Dataset assembled by Superset for the **Campus Beats 2026** Tech Challenge in partnership with ZS Associates.
For clarifications during the challenge, use the official Slack/Discord channel announced with your participant brief.

Good luck — and enjoy.
