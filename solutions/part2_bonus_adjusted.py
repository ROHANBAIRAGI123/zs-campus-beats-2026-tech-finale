"""
Part 2 (Bonus): Adjusted Growth & Trend Analysis
=================================================
Calculates an "Adjusted Quarter-on-Quarter Growth Rate" that removes 
distortions caused by noise in the data.

Adjustment Logic & Justification:
1. One-time promotions: We completely exclude revenue from items where a 
   promotion was applied (`promo_id_applied IS NOT NULL`). Promos artificially 
   inflate demand and distort the underlying organic growth baseline.
2. Unusually high return spikes: We cap return deductions at 5% of gross revenue. 
   If a quarter had an abnormal 15% return rate due to a product defect, capping 
   it prevents that isolated spike from ruining the quarter's organic trend.
3. Temporary store closures: If a region had stores affected by a `full_closure` 
   event (e.g. flood, strike), we apply a +5% upward adjustment to the region's 
   revenue for that quarter to approximate what sales *would* have been.

Usage:
    python solutions/part2_bonus_adjusted.py
"""

import duckdb
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "zs_challenge.duckdb"

def run():
    if not DB_PATH.exists():
        sys.exit(f"Database not found at {DB_PATH}.")

    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    print(f"\n{'='*80}")
    print(f"  Part 2 (Bonus): Adjusted QoQ Growth (Signal vs Noise)")
    print(f"{'='*80}\n")

    query = """
    WITH
    target_quarters AS (
        SELECT DISTINCT quarter, MIN(date) as q_start, MAX(date) as q_end
        FROM calendar
        WHERE quarter <= '2026Q1'
        GROUP BY quarter
        ORDER BY quarter DESC
        LIMIT 7 
    ),
    store_region AS (
        SELECT sgm.store_id, sgm.region_id, sgm.region_name, tq.quarter
        FROM store_geo_mapping sgm
        CROSS JOIN target_quarters tq
        WHERE sgm.effective_from <= CAST(tq.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(tq.q_start AS VARCHAR))
    ),
    
    -- Adjustment 3: Identify closure events to apply a +5% correction later
    closure_events AS (
        SELECT DISTINCT sr.region_name, tq.quarter, 1 AS had_closure
        FROM store_events se
        CROSS JOIN target_quarters tq
        JOIN store_region sr ON se.store_id = sr.store_id AND sr.quarter = tq.quarter
        WHERE se.event_type IN ('flood_closure', 'strike', 'system_outage')
          AND se.impact_severity = 'full_closure'
          AND se.start_date <= CAST(tq.q_end AS VARCHAR)
          AND (se.end_date IS NULL OR se.end_date >= CAST(tq.q_start AS VARCHAR))
    ),

    -- Adjustment 1: Calculate Gross Revenue ONLY from organic, non-promotional sales
    organic_gross_revenue AS (
        SELECT oi.store_id, tq.quarter, SUM(oi.line_total) AS organic_gross_rev
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN target_quarters tq ON c.quarter = tq.quarter
        WHERE o.order_status = 'completed' 
          AND oi.is_cancelled = 0
          AND (oi.promo_id_applied IS NULL OR oi.promo_id_applied = '') -- Exclude Promos
        GROUP BY oi.store_id, tq.quarter
    ),
    
    -- Refund deductions
    return_deductions AS (
        SELECT oi.store_id, tq.quarter, SUM(r.refund_amount) AS refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN orders o ON r.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN target_quarters tq ON c.quarter = tq.quarter
        WHERE r.refund_status = 'refunded'
        GROUP BY oi.store_id, tq.quarter
    ),
    
    -- Aggregate by Region and apply Adjustment 2 (Cap returns at 5% of gross) 
    -- and Adjustment 3 (Multiply by 1.05 if closures happened)
    adjusted_regional_revenue AS (
        SELECT 
            sr.region_name,
            sr.quarter,
            SUM(
                (gr.organic_gross_rev - LEAST(COALESCE(rd.refunds, 0), gr.organic_gross_rev * 0.05)) 
                * CASE WHEN ce.had_closure = 1 THEN 1.05 ELSE 1.0 END
            ) as adj_net_revenue
        FROM store_region sr
        JOIN organic_gross_revenue gr ON sr.store_id = gr.store_id AND sr.quarter = gr.quarter
        LEFT JOIN return_deductions rd ON sr.store_id = rd.store_id AND sr.quarter = rd.quarter
        LEFT JOIN closure_events ce ON sr.region_name = ce.region_name AND sr.quarter = ce.quarter
        GROUP BY sr.region_name, sr.quarter
    ),
    
    -- Calculate Growth
    growth_calc AS (
        SELECT 
            arr.region_name,
            arr.quarter,
            arr.adj_net_revenue,
            LAG(arr.adj_net_revenue) OVER(PARTITION BY arr.region_name ORDER BY arr.quarter) AS prev_adj_revenue
        FROM adjusted_regional_revenue arr
    )
    
    SELECT 
        region_name,
        quarter,
        ROUND(adj_net_revenue, 2) AS adjusted_metric_value,
        ROUND(prev_adj_revenue, 2) AS prev_quarter_adjusted_value,
        ROUND(((adj_net_revenue - prev_adj_revenue) / prev_adj_revenue) * 100, 2) AS adjusted_qoq_growth_pct
    FROM growth_calc
    WHERE prev_adj_revenue IS NOT NULL
    ORDER BY region_name, quarter DESC;
    """
    
    print(">>> Calculating ADJUSTED Quarter-over-Quarter Growth Rates...\n")
    df = con.execute(query).fetchdf()
    
    if df.empty:
        print("No data found.")
    else:
        print(df.to_string(index=False))
        
    con.close()

if __name__ == "__main__":
    run()
