
# Superset × ZS Associates **Campus Beats 2026** **Tech Challenge** 

---

#  **Confidential — For ZS Associates & Superset teams** **Date:**19 Mar 2026 

# **ZS Tech Challenge | Group Activity |  Problem Statement** 

## **Theme: Retail Network Intelligence Challenge**

You are given data from a large multi-city retail network operating across physical stores, dark stores, and online-assisted fulfilment centres.

The business wants to understand:

* which stores are truly performing well,  
* how demand is changing over time,  
* and what is likely to happen next quarter.

The dataset is intentionally messy and realistic.  
Participants will need to combine multiple tables, resolve ambiguity, handle missing and contradictory records, account for returns/cancellations, and apply business logic carefully.

Each part can be solved independently.

---

# **Dataset Context**

Participants will receive a relational dataset containing tables such as:

* `stores`  
* `store_geo_mapping`  
* `products`  
* `categories`  
* `orders`  
* `order_items`  
* `returns`  
* `customers`  
* `promotions`  
* `inventory_snapshots`  
* `calendar`  
* `store_events`  
* `pricing_history`

The data is designed to reflect real-world complexity:

* stores can change regions over time,  
* products can belong to hierarchical categories,  
* orders may contain multiple items and partial returns,  
* promotions can overlap,  
* revenue and gross sales are not the same,  
* some stores may be temporarily shut or under renovation,  
* inventory stockouts may distort demand,  
* dates may need quarter mapping from a calendar table,  
* certain metrics require excluding abnormal events.

Participants must infer the correct business logic from the data dictionary and problem conditions.

---

# **Part 1: Store Performance Intelligence**

## **Main Challenge**

Identify the **3rd highest performing store** in each metro region for a given product super-category during the most recent completed quarter.

### **Business definition of performance**

Performance should be computed using **net realized revenue**, where:

* gross item sales are included,  
* cancelled items are excluded,  
* returned items are deducted,  
* promotional discounts are accounted for,  
* only completed transactions are valid,  
* stores marked inactive during the quarter must be excluded.

### **Output expectation**

For each metro region:

* region name  
* store id  
* store name  
* net realized revenue  
* rank within region

### **What this tests**

* joins across many tables  
* handling returns and cancellations correctly  
* quarter logic  
* ranking/window functions  
* filtering based on slowly changing operational metadata

## **Bonus Challenge**

Among those ranked stores, identify the one with the **best revenue efficiency**, defined as:

**net realized revenue / effective in-stock days**

Where:

* effective in-stock days must be derived from inventory snapshots,  
* days when a store was closed for renovation should not count,  
* only days when at least 70% of SKUs in the target category were available should be treated as valid stock days.

### **What this tests**

* advanced aggregation  
* derived business metrics  
* handling incomplete inventory data  
* reasoning beyond basic ranking queries

---

# **Part 2: Growth and Trend Analysis**

## **Main Challenge**

Calculate the **quarter-on-quarter growth rate** of a selected business metric for each region over the last 6 completed quarters.

Participants may be asked to calculate one of the following:

* net realized revenue  
* unique purchasing customers  
* average basket value  
* units sold in premium categories

### **Rules**

* growth must be computed only for comparable quarters,  
* stores that were launched mid-quarter should be treated carefully,  
* quarters heavily impacted by exceptional events (for example flood closure, strike, migration outage) should be flagged using the `store_events` table,  
* if the denominator quarter is zero or invalid, growth handling should be explicitly defined.

### **Output expectation**

For each region and quarter:

* region  
* quarter  
* metric value  
* previous quarter value  
* QoQ growth %  
* event-adjusted flag

### **What this tests**

* time-series SQL  
* lag/window functions  
* robust denominator handling  
* business-quality metric definitions  
* anomaly-aware analysis

## **Bonus Challenge**

Create an **adjusted growth metric** that removes distortions caused by:

* temporary store closures,  
* severe stockouts,  
* one-time promotion campaigns,  
* unusually high return spikes.

Participants must define and justify their adjustment logic.

### **What this tests**

* analytical maturity  
* separating signal from noise  
* designing assumptions instead of blindly querying

---

# **Part 3: Forward-Looking Business Insight**

## **Main Challenge**

Predict the **next quarter value** of a target metric for each region-category pair.

Suggested target metrics:

* net realized revenue  
* units sold  
* repeat customer rate

Participants are not required to use ML.  
A strong logic-based forecasting approach is acceptable if it is well reasoned.

### **Constraints**

Forecasts should consider:

* recent quarter trends,  
* seasonality,  
* stock availability patterns,  
* promotion intensity,  
* store openings/closures,  
* category-specific volatility.

### **Output expectation**

For each region-category pair:

* region  
* category  
* predicted metric for next quarter  
* method used  
* confidence or reliability tag

### **What this tests**

* structured forecasting logic  
* feature reasoning from relational data  
* ability to translate business data into predictive rules

## **Bonus Challenge**

Generate a **scenario-based forecast**:

* baseline forecast  
* optimistic forecast  
* constrained forecast

Where assumptions may vary by:

* stock availability,  
* return rates,  
* promo intensity,  
* operational disruptions.

Participants must also identify the **top 3 drivers** influencing their forecast.

### **What this tests**

* advanced reasoning  
* modeling assumptions explicitly  
* business storytelling with data

---

# **Part 4: Retail Intelligence Copilot — AI Agent Design**

## **Main Challenge**

Design (and prototype, if time permits) an **AI agent** that lets non-technical business stakeholders — regional managers, category heads, finance leads — ask questions of this dataset in **natural language** and receive grounded, traceable answers.

Imagine a regional manager typing:

* *"Why did Mumbai's electronics revenue drop in 2024 Q3?"*  
* *"Which 3 stores in Pune are at most risk next quarter, and why?"*  
* *"Show me promotions overlapping during Diwali week and the SKUs they covered."*  
* *"Compare top-3 dark stores in Bengaluru by revenue per in-stock day for the last 4 quarters."*

The agent should answer accurately, cite the data it used, and gracefully handle ambiguity, missing data, and out-of-scope questions.

### **Design constraints**

Your agent must reason about:

* which tables / queries to invoke for a given question  
* how to resolve business terms ("last quarter", "Mumbai", "premium electronics") to dataset entities (`2026Q1`, `MUM`, specific `super_category_id`s)  
* how to handle real-world data-quality issues without misleading the user  
* how to detect when a question is **out of scope** or **under-specified** and ask back  
* how to **cite** which rows / aggregations the answer is based on, so a manager can audit  
* how to bound cost and latency (LLM call budget, max tool-call depth)

Treat Parts 1, 2, and 3 as **tools** your agent can invoke — your forecasting logic, store ranking, QoQ growth, etc. should be exposed as callable functions, not re-derived inside the LLM.

### **Output expectation (deliverables)**

A submission folder containing:

1. **Architecture diagram** — model choice, tool layer, semantic layer (entity resolution), retrieval (e.g. data dictionary in vector store), memory, guardrails, observability, and how outputs from Parts 1–3 plug in as tools.  
2. **Tool catalog** — at least 5 callable tools with name, JSON-schema input/output, and a one-line description of when the agent should call each. Examples: `get_store_performance`, `get_qoq_trend`, `forecast_next_quarter`, `find_store_events`, `get_inventory_health`.  
3. **System prompt + few-shot examples** (2–3 worked examples covering happy path, ambiguous query, out-of-scope query).  
4. **Evaluation plan** — how you would measure correctness (test-set construction, scoring rubric), how you'd detect hallucination, target latency / cost budgets per query.  
5. **Risk register** — at minimum: hallucinated numbers, PII leakage (customer table), prompt injection through stored data (e.g. malicious `event.description`), runaway tool loops, stale-data risk. For each, a one-line mitigation.  
6. **Three end-to-end sample dialogues** showing the agent's reasoning, tool calls, and final answer with citations:  
   * a happy-path question  
   * an ambiguous question that the agent must clarify  
   * an adversarial / out-of-scope query that the agent must refuse safely  
7. **(Strongly encouraged, not required) a working prototype** — a CLI / notebook with at least 2 tools wired to a real LLM, demonstrating one of the sample dialogues live.

### **What this tests**

* end-to-end AI system design (not just prompting)  
* tool-design and function-calling discipline  
* hallucination control via grounding and citations  
* evaluation thinking — how do you *know* the agent is right?  
* understanding of where LLMs fail and where deterministic code should take over  
* product sensitivity to non-technical stakeholders

## **Bonus Challenge**

Extend the copilot into an **Autonomous Anomaly Investigator** that runs **without a human prompt**.

Trigger condition: any region whose net realized revenue QoQ growth crosses a threshold (e.g. **< −10%**, ignoring known seasonality), or any store-quarter where stockout-adjusted revenue diverges sharply from forecast.

When triggered, the same agent must:

* form an investigation **plan** (which tables / time windows to inspect)  
* execute that plan via tool calls, possibly across multiple steps  
* reason about whether the drop is explained by a known event (`store_events`), a stockout, a return spike, a promo wind-down, or something genuinely unexplained  
* know when to **stop** investigating (define a stopping criterion — confidence threshold, max steps, diminishing-return signal)  
* produce a one-page written **exec summary** for the regional manager: what happened, suspected cause, supporting evidence with citations, recommended next action, and a confidence rating

### **Output expectation**

* the **agent loop design** (planner → executor → evaluator → writer; or your alternative)  
* the **stopping criterion** and how you tuned it  
* **two worked investigations** on actual triggers from the dataset (e.g. Mumbai 2024Q3, Bengaluru 2025Q3)  
* a brief **self-evaluation**: where did the agent over-investigate? where did it stop too early? what would you change?

### **What this tests**

* autonomous-agent loop design (plan / act / observe / decide-to-stop)  
* multi-step reasoning grounded in real data  
* writing for executive audiences, not engineers  
* honest self-critique of agent behaviour


