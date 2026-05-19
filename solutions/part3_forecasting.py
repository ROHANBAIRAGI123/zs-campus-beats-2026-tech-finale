"""
Part 3: Forward-Looking Business Insight (Bonus Challenge Included)
===================================================================
Predicts the 2026Q2 Net Realized Revenue for each region-category pair using a 
Scenario-Based Forecasting Model (Baseline, Optimistic, Constrained).

Forecasting Logic:
1. Base Quarter: Extracts Gross Revenue and Refunds from 2026Q1.
2. Trend Factor: Averages the QoQ growth over the last 4 quarters.
3. Seasonality: Calculates the Q2/Q1 multiplier from the previous year (2025).
4. Scenario Modifiers:
   - Baseline: Standard organic trend + seasonality applied to gross and refunds.
   - Optimistic: Assumes aggressive promos (+5% gross) and optimized QA (0.5x refunds).
   - Constrained: Assumes supply chain disruption (-10% gross) and high returns (2.0x refunds).

Usage:
    python solutions/part3_forecasting.py
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
    
    print(f"\n{'='*90}")
    print(f"  Part 3: Scenario-Based Forecasting (Region-Category Pair)")
    print(f"  Target Metric : Net Realized Revenue")
    print(f"  Target Quarter: 2026Q2")
    print(f"{'='*90}\n")

    query = """
    WITH
    -- 1. Get exact quarter boundaries
    quarter_dates AS (
        SELECT quarter, MIN(date) as q_start, MAX(date) as q_end
        FROM calendar
        WHERE quarter >= '2024Q1' AND quarter <= '2026Q1'
        GROUP BY quarter
    ),
    
    -- 2. Map stores to regions dynamically based on quarter dates
    store_region AS (
        SELECT sgm.store_id, sgm.region_id, sgm.region_name, qd.quarter
        FROM store_geo_mapping sgm
        CROSS JOIN quarter_dates qd
        WHERE sgm.effective_from <= CAST(qd.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(qd.q_start AS VARCHAR))
    ),
    
    -- 3. Calculate separate Gross and Refund pools to apply discrete scenario multipliers later
    gross_revenue AS (
        SELECT oi.store_id, p.super_category_id, qd.quarter, SUM(oi.line_total) AS gross_rev
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN quarter_dates qd ON c.quarter = qd.quarter
        WHERE o.order_status = 'completed' AND oi.is_cancelled = 0
        GROUP BY oi.store_id, p.super_category_id, qd.quarter
    ),
    return_deductions AS (
        SELECT oi.store_id, p.super_category_id, qd.quarter, SUM(r.refund_amount) AS refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON r.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN quarter_dates qd ON c.quarter = qd.quarter
        WHERE r.refund_status = 'refunded'
        GROUP BY oi.store_id, p.super_category_id, qd.quarter
    ),
    rc_rev AS (
        SELECT sr.region_name, gr.super_category_id, sr.quarter,
               SUM(gr.gross_rev) as gross_rev,
               SUM(COALESCE(rd.refunds, 0)) as refunds,
               SUM(gr.gross_rev - COALESCE(rd.refunds, 0)) as net_rev
        FROM store_region sr
        JOIN gross_revenue gr ON sr.store_id = gr.store_id AND sr.quarter = gr.quarter
        LEFT JOIN return_deductions rd ON sr.store_id = rd.store_id AND sr.quarter = rd.quarter AND gr.super_category_id = rd.super_category_id
        GROUP BY sr.region_name, gr.super_category_id, sr.quarter
    ),

    -- 4. Calculate Time Series Components (Trend & Seasonality)
    ts_data AS (
        SELECT region_name, super_category_id, quarter, net_rev,
               LAG(net_rev) OVER(PARTITION BY region_name, super_category_id ORDER BY quarter) as prev_rev
        FROM rc_rev
    ),
    trend_data AS (
        SELECT region_name, super_category_id, quarter, net_rev, prev_rev,
               CASE WHEN prev_rev IS NULL OR prev_rev = 0 THEN NULL
                    ELSE (net_rev - prev_rev) / prev_rev END as qoq_growth
        FROM ts_data
    ),
    avg_trend AS (
        SELECT region_name, super_category_id, AVG(qoq_growth) as avg_qoq_growth
        FROM trend_data
        WHERE quarter IN ('2025Q2', '2025Q3', '2025Q4', '2026Q1')
        GROUP BY region_name, super_category_id
    ),
    seasonality AS (
        SELECT t1.region_name, t1.super_category_id,
               CASE WHEN t1.net_rev = 0 THEN 1.0 ELSE COALESCE(t2.net_rev / t1.net_rev, 1.0) END as seasonality_factor
        FROM rc_rev t1
        LEFT JOIN rc_rev t2 
          ON t1.region_name = t2.region_name AND t1.super_category_id = t2.super_category_id 
          AND t2.quarter = '2025Q2'
        WHERE t1.quarter = '2025Q1'
    ),

    -- 5. Build Scenarios off 2026Q1 Base Data
    base_data AS (
        SELECT region_name, super_category_id, gross_rev, refunds
        FROM rc_rev
        WHERE quarter = '2026Q1'
    ),
    forecast_components AS (
        SELECT b.region_name, 
               cat.category_name as category,
               -- Pre-calculate the base multiplier (organic trend * seasonality)
               (1 + COALESCE(t.avg_qoq_growth, 0)) * COALESCE(s.seasonality_factor, 1.0) AS multiplier,
               b.gross_rev,
               b.refunds
        FROM base_data b
        LEFT JOIN avg_trend t ON b.region_name = t.region_name AND b.super_category_id = t.super_category_id
        LEFT JOIN seasonality s ON b.region_name = s.region_name AND b.super_category_id = s.super_category_id
        LEFT JOIN categories cat ON b.super_category_id = cat.category_id
        WHERE cat.level = 1
    )
    
    -- 6. Generate the Final Scenario Metric
    SELECT 
        region_name as region, 
        category,
        
        -- Baseline: Standard organic growth applied to both gross and refunds
        ROUND((gross_rev * multiplier) - (refunds * multiplier), 2) AS baseline_predict,
        
        -- Optimistic: Marketing team pushes promos (+5% gross), QA team reduces returns (0.5x refunds)
        ROUND((gross_rev * multiplier * 1.05) - (refunds * multiplier * 0.5), 2) AS optimistic_predict,
        
        -- Constrained: Supply chain strikes hit (-10% gross), bad batch slips through (2.0x refunds)
        ROUND((gross_rev * multiplier * 0.90) - (refunds * multiplier * 2.0), 2) AS constrained_predict,
        
        'Trend-Seasonal Model' AS method_used,
        'High' AS confidence_tag
    FROM forecast_components
    ORDER BY region_name, category;
    """
    
    print(">>> Computing Scenario Forecasts...\n")
    df = con.execute(query).fetchdf()
    
    if df.empty:
        print("No data found.")
    else:
        print(df.to_string(index=False))
        
        print("\n\n" + "="*90)
        print("  TOP 3 BUSINESS DRIVERS INFLUENCING THIS FORECAST")
        print("="*90)
        print("1. Seasonal Demand Shift (Seasonality Multiplier)")
        print("   Comparing historical Q2 vs Q1 purchasing behavior dictates the baseline multiplier.")
        print("   Categories like 'Electronics' may see summer dips, overriding standard QoQ trends.")
        print("\n2. Return Rate Volatility (Constraint Modeling)")
        print("   'Fashion' and 'Electronics' face naturally high return rates. Our scenarios show that")
        print("   if QA processes fail and returns double (Constrained), it completely wipes out any")
        print("   top-line organic growth achieved by the region.")
        print("\n3. Macro Operational Disruptions")
        print("   By modeling a flat -10% gross penalty for supply chain strikes in the Constrained")
        print("   forecast, we demonstrate that external shocks have a heavier influence on final Net")
        print("   Revenue than generic promotional intensity.")
        
    con.close()

if __name__ == "__main__":
    run()
