"""
Part 1: Store Performance Intelligence
=======================================
Find the 3rd highest performing store in EACH metro region for EACH product
super-category during the most recent completed quarter (2026-Q1).

Performance = Net Realized Revenue:
  + SUM(order_items.line_total) for completed orders, non-cancelled items
  - SUM(returns.refund_amount) for refunded returns

Usage:
    python solutions/part1_store_performance.py
"""

import duckdb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "zs_challenge.duckdb"

def run(quarter="2026Q1"):
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    print(f"\n{'='*80}")
    print(f"  Part 1: Store Performance Intelligence")
    print(f"  Quarter: {quarter}")
    print(f"  Goal   : 3rd highest store in EVERY Region for EVERY Super-Category")
    print(f"{'='*80}\n")

    query = f"""
    WITH
    -- Step 1: Quarter date boundaries
    quarter_dates AS (
        SELECT MIN(date) AS q_start, MAX(date) AS q_end
        FROM calendar WHERE quarter = '{quarter}'
    ),

    -- Step 2: Store → Region mapping using SCD table
    store_region AS (
        SELECT sgm.store_id, sgm.region_id, sgm.region_name
        FROM store_geo_mapping sgm
        CROSS JOIN quarter_dates qd
        WHERE sgm.effective_from <= CAST(qd.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(qd.q_start AS VARCHAR))
    ),

    -- Step 3: Exclude stores inactive during the quarter
    inactive_stores AS (
        SELECT DISTINCT se.store_id
        FROM store_events se
        CROSS JOIN quarter_dates qd
        WHERE se.event_type IN ('permanent_closure', 'renovation')
          AND se.impact_severity = 'full_closure'
          AND se.start_date <= CAST(qd.q_end AS VARCHAR)
          AND (se.end_date IS NULL OR se.end_date >= CAST(qd.q_start AS VARCHAR))
    ),

    -- Step 4: Gross item revenue per store AND super_category
    gross_revenue AS (
        SELECT oi.store_id, p.super_category_id, SUM(oi.line_total) AS gross_item_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        CROSS JOIN quarter_dates qd
        WHERE o.order_status = 'completed' AND oi.is_cancelled = 0
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
        GROUP BY oi.store_id, p.super_category_id
    ),

    -- Step 5: Return deductions (refunded only) per store AND super_category
    return_deductions AS (
        SELECT oi.store_id, p.super_category_id, SUM(r.refund_amount) AS total_refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN orders o ON r.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        CROSS JOIN quarter_dates qd
        WHERE r.refund_status = 'refunded'
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
        GROUP BY oi.store_id, p.super_category_id
    ),

    -- Step 6: Net realized revenue
    store_performance AS (
        SELECT gr.store_id, gr.super_category_id,
            gr.gross_item_revenue - COALESCE(rd.total_refunds, 0) AS net_realized_revenue
        FROM gross_revenue gr
        LEFT JOIN return_deductions rd 
          ON gr.store_id = rd.store_id AND gr.super_category_id = rd.super_category_id
    ),

    -- Step 7: Rank within each region AND super_category combination
    ranked AS (
        SELECT sr.region_name, 
               c.category_name AS super_category, 
               sp.store_id, 
               s.store_name,
               ROUND(sp.net_realized_revenue, 2) AS net_realized_revenue,
               RANK() OVER (
                   PARTITION BY sr.region_id, sp.super_category_id 
                   ORDER BY sp.net_realized_revenue DESC
               ) AS rank_in_region
        FROM store_performance sp
        JOIN store_region sr ON sp.store_id = sr.store_id
        JOIN stores s ON sp.store_id = s.store_id
        JOIN categories c ON sp.super_category_id = c.category_id
        WHERE sp.store_id NOT IN (SELECT store_id FROM inactive_stores)
    )

    -- Step 8: Final Output -> 3rd highest store
    SELECT region_name, super_category, store_id, store_name, net_realized_revenue, rank_in_region
    FROM ranked
    WHERE rank_in_region = 3
    ORDER BY region_name, super_category;
    """

    print(">>> Main Challenge Results:\n")
    result = con.execute(query).fetchdf()

    if result.empty:
        print("  No results found.")
    else:
        print(result.to_string(index=False))
        print()

    con.close()

if __name__ == "__main__":
    run()
