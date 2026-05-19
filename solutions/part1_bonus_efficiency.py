"""
Part 1 (Bonus): Revenue Efficiency
==================================
Identifies the store with the best 'revenue efficiency' among the top ranked stores.
Efficiency = net realized revenue / effective in-stock days

Rules for effective in-stock days:
1. Derived from `inventory_snapshots`.
2. Renovation days do NOT count.
3. Valid days require >= 70% of SKUs in the category to be available.

Usage:
    python solutions/part1_bonus_efficiency.py
"""

import duckdb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "zs_challenge.duckdb"

def run(category_id='CAT0004', quarter='2026Q1'):
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    print(f"\n{'='*80}")
    print(f"  Part 1 (Bonus): Revenue Efficiency")
    print(f"  Quarter : {quarter}")
    print(f"  Category: {category_id}")
    print(f"{'='*80}\n")

    query = f"""
    WITH
    -- 1. Base configuration
    quarter_dates AS (
        SELECT MIN(date) AS q_start, MAX(date) AS q_end
        FROM calendar WHERE quarter = '{quarter}'
    ),
    store_region AS (
        SELECT sgm.store_id, sgm.region_id, sgm.region_name
        FROM store_geo_mapping sgm
        CROSS JOIN quarter_dates qd
        WHERE sgm.effective_from <= CAST(qd.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(qd.q_start AS VARCHAR))
    ),
    inactive_stores AS (
        SELECT DISTINCT se.store_id
        FROM store_events se
        CROSS JOIN quarter_dates qd
        WHERE se.event_type IN ('permanent_closure', 'renovation')
          AND se.impact_severity = 'full_closure'
          AND se.start_date <= CAST(qd.q_end AS VARCHAR)
          AND (se.end_date IS NULL OR se.end_date >= CAST(qd.q_start AS VARCHAR))
    ),
    
    -- 2. Net Revenue Calculation
    gross_revenue AS (
        SELECT oi.store_id, SUM(oi.line_total) AS gross_item_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        CROSS JOIN quarter_dates qd
        WHERE o.order_status = 'completed' AND oi.is_cancelled = 0
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
          AND p.super_category_id = '{category_id}'
        GROUP BY oi.store_id
    ),
    return_deductions AS (
        SELECT oi.store_id, SUM(r.refund_amount) AS total_refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN orders o ON r.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        CROSS JOIN quarter_dates qd
        WHERE r.refund_status = 'refunded'
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
          AND p.super_category_id = '{category_id}'
        GROUP BY oi.store_id
    ),
    store_performance AS (
        SELECT gr.store_id,
            gr.gross_item_revenue - COALESCE(rd.total_refunds, 0) AS net_realized_revenue
        FROM gross_revenue gr
        LEFT JOIN return_deductions rd ON gr.store_id = rd.store_id
    ),
    
    -- 3. Get Top 5 stores per region to evaluate efficiency
    ranked_stores AS (
        SELECT sr.region_name, sp.store_id, sp.net_realized_revenue,
            DENSE_RANK() OVER (PARTITION BY sr.region_name ORDER BY sp.net_realized_revenue DESC) AS rank_in_region
        FROM store_performance sp
        JOIN store_region sr ON sp.store_id = sr.store_id
        WHERE sp.store_id NOT IN (SELECT store_id FROM inactive_stores)
    ),
    top_ranked AS (
        SELECT * FROM ranked_stores WHERE rank_in_region <= 5
    ),

    -- 4. BONUS LOGIC: Calculate Effective In-Stock Days
    renovation_days AS (
        -- Map renovation date ranges to actual dates using the calendar
        SELECT se.store_id, c.date as closure_date
        FROM store_events se
        JOIN calendar c 
          ON CAST(c.date AS VARCHAR) >= se.start_date 
         AND (se.end_date IS NULL OR CAST(c.date AS VARCHAR) <= se.end_date)
        WHERE se.event_type = 'renovation'
    ),
    daily_inventory AS (
        -- Only query snapshots for the top ranked stores
        SELECT ins.store_id, ins.snapshot_date,
               COUNT(*) AS total_assorted_skus,
               SUM(CASE WHEN ins.is_in_stock = 1 THEN 1 ELSE 0 END) AS available_skus
        FROM inventory_snapshots ins
        JOIN products p ON ins.product_id = p.product_id
        JOIN top_ranked tr ON ins.store_id = tr.store_id
        CROSS JOIN quarter_dates qd
        WHERE p.super_category_id = '{category_id}'
          AND ins.snapshot_date >= qd.q_start AND ins.snapshot_date <= qd.q_end
        GROUP BY ins.store_id, ins.snapshot_date
    ),
    effective_stock_days AS (
        -- Snapshots are taken weekly in this dataset. We multiply by 7 to estimate 'days'
        SELECT di.store_id, COUNT(*) * 7 AS valid_days
        FROM daily_inventory di
        LEFT JOIN renovation_days rd 
               ON di.store_id = rd.store_id AND di.snapshot_date = rd.closure_date
        WHERE rd.closure_date IS NULL -- Rule: Renovation days do NOT count
          AND (di.available_skus * 1.0 / di.total_assorted_skus) >= 0.70 -- Rule: 70% threshold
        GROUP BY di.store_id
    ),
    
    -- 5. Calculate Final Revenue Efficiency
    efficiency_calc AS (
        SELECT 
            tr.region_name, 
            tr.store_id,
            tr.rank_in_region,
            ROUND(tr.net_realized_revenue, 2) AS net_realized_revenue,
            COALESCE(esd.valid_days, 0) AS effective_in_stock_days,
            CASE WHEN COALESCE(esd.valid_days, 0) = 0 THEN NULL
                 ELSE ROUND(tr.net_realized_revenue / esd.valid_days, 2)
            END AS revenue_efficiency
        FROM top_ranked tr
        LEFT JOIN effective_stock_days esd ON tr.store_id = esd.store_id
    )
    
    -- Pick the #1 most efficient store per region
    SELECT *
    FROM (
        SELECT *, DENSE_RANK() OVER (PARTITION BY region_name ORDER BY revenue_efficiency DESC) as efficiency_rank
        FROM efficiency_calc
    )
    WHERE efficiency_rank = 1
    ORDER BY region_name;
    """
    
    print(">>> Analyzing Inventory Snapshots for Revenue Efficiency...\n")
    df = con.execute(query).fetchdf()
    
    if df.empty:
        print("No results found.")
    else:
        print(df.to_string(index=False))
        
    con.close()

if __name__ == "__main__":
    run()
