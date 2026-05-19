"""
Part 2: Growth and Trend Analysis
==================================
Calculate the quarter-on-quarter (QoQ) growth rate of net realized revenue
for each region over the last 6 completed quarters.

Rules Addressed:
1. Comparable quarters: We use Same-Store Sales logic. Stores launched 
   mid-quarter are excluded from that quarter's calculation to prevent 
   artificial growth spikes.
2. Exceptional Events: Quarters impacted by floods, strikes, etc., are flagged.
3. Zero Denominator: Explicitly handled using NULLIF to prevent divide-by-zero.

Usage:
    python solutions/part2_growth_analysis.py
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
    print(f"  Part 2: QoQ Growth & Trend Analysis (Net Realized Revenue)")
    print(f"{'='*80}\n")

    query = """
    WITH
    -- Step 1: Get the last 6 completed quarters (+1 for previous quarter lag)
    target_quarters AS (
        SELECT DISTINCT quarter, MIN(date) as q_start, MAX(date) as q_end
        FROM calendar
        WHERE quarter <= '2026Q1'
        GROUP BY quarter
        ORDER BY quarter DESC
        LIMIT 7 
    ),
    
    -- Step 2: Store to Region mapping per quarter
    store_region AS (
        SELECT 
            sgm.store_id, 
            sgm.region_id, 
            sgm.region_name,
            tq.quarter,
            tq.q_start,
            tq.q_end
        FROM store_geo_mapping sgm
        CROSS JOIN target_quarters tq
        WHERE sgm.effective_from <= CAST(tq.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(tq.q_start AS VARCHAR))
    ),
    
    -- Step 3: Flag quarters with significant events per region
    regional_events AS (
        SELECT DISTINCT 
            sr.region_name,
            tq.quarter,
            1 AS has_event
        FROM store_events se
        CROSS JOIN target_quarters tq
        JOIN store_region sr ON se.store_id = sr.store_id AND sr.quarter = tq.quarter
        WHERE se.event_type IN ('flood_closure', 'strike', 'system_outage')
          AND se.start_date <= CAST(tq.q_end AS VARCHAR)
          AND (se.end_date IS NULL OR se.end_date >= CAST(tq.q_start AS VARCHAR))
    ),

    -- Step 4: Gross revenue per store per quarter 
    -- RULE CHECK: Exclude stores launched mid-quarter
    gross_revenue AS (
        SELECT 
            oi.store_id,
            tq.quarter,
            SUM(oi.line_total) AS gross_rev
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN target_quarters tq ON c.quarter = tq.quarter
        JOIN stores s ON oi.store_id = s.store_id
        WHERE o.order_status = 'completed' 
          AND oi.is_cancelled = 0
          -- Treat stores launched mid-quarter carefully by excluding them 
          -- until they have been open for a full quarter.
          AND s.launch_date < tq.q_start
        GROUP BY oi.store_id, tq.quarter
    ),
    
    -- Step 5: Refund deductions per store per quarter
    return_deductions AS (
        SELECT 
            oi.store_id,
            tq.quarter,
            SUM(r.refund_amount) AS refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN orders o ON r.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN target_quarters tq ON c.quarter = tq.quarter
        WHERE r.refund_status = 'refunded'
        GROUP BY oi.store_id, tq.quarter
    ),
    
    -- Step 6: Net Revenue per Region per Quarter
    regional_revenue AS (
        SELECT 
            sr.region_name,
            sr.quarter,
            SUM(gr.gross_rev - COALESCE(rd.refunds, 0)) as net_revenue
        FROM store_region sr
        JOIN gross_revenue gr ON sr.store_id = gr.store_id AND sr.quarter = gr.quarter
        LEFT JOIN return_deductions rd ON sr.store_id = rd.store_id AND sr.quarter = rd.quarter
        GROUP BY sr.region_name, sr.quarter
    ),
    
    -- Step 7: Calculate QoQ Growth
    growth_calc AS (
        SELECT 
            rr.region_name,
            rr.quarter,
            rr.net_revenue,
            LAG(rr.net_revenue) OVER(PARTITION BY rr.region_name ORDER BY rr.quarter) AS prev_revenue,
            COALESCE(re.has_event, 0) AS event_flag
        FROM regional_revenue rr
        LEFT JOIN regional_events re ON rr.region_name = re.region_name AND rr.quarter = re.quarter
    )
    
    -- Step 8: Final formatting with zero-denominator handling
    SELECT 
        region_name,
        quarter,
        ROUND(net_revenue, 2) AS metric_value,
        ROUND(prev_revenue, 2) AS prev_quarter_value,
        -- RULE CHECK: Handle zero/invalid denominator explicitly
        CASE 
            WHEN prev_revenue IS NULL THEN NULL
            WHEN prev_revenue = 0 THEN NULL 
            ELSE ROUND(((net_revenue - prev_revenue) / prev_revenue) * 100, 2) 
        END AS qoq_growth_pct,
        CASE WHEN event_flag = 1 THEN 'Yes (Impacted)' ELSE 'No' END AS event_adjusted_flag
    FROM growth_calc
    WHERE prev_revenue IS NOT NULL -- Exclude the 7th quarter used only for lag calculation
    ORDER BY region_name, quarter DESC;
    """
    
    print(">>> Calculating Quarter-over-Quarter Growth Rates...\n")
    df = con.execute(query).fetchdf()
    
    if df.empty:
        print("No data found.")
    else:
        print(df.to_string(index=False, na_rep='NULL'))
        print("\nNote: 'Yes (Impacted)' means the region had stores affected by flood, strike, or outage during that quarter.")
        
    con.close()

if __name__ == "__main__":
    run()
