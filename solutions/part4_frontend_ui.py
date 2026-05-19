"""
Part 4: Retail Intelligence Copilot (Streamlit Frontend UI)
===========================================================
A beautiful web-based chat interface that wraps the Gemini AI Agent 
and connects it to the DuckDB SQL tools.

Usage:
    streamlit run solutions/part4_frontend_ui.py
"""

import streamlit as st
import duckdb
import pandas as pd
from google import genai
from google.genai import types
import os
import json
from pathlib import Path

# --- Configuration & Setup ---
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "zs_challenge.duckdb"

st.set_page_config(page_title="ZS Retail Copilot", page_icon="🤖", layout="centered")

# --- TOOL 1: Store Performance ---
def get_store_performance(region_name: str, quarter: str = '2026Q1', super_category_id: str = 'CAT0004') -> str:
    """
    Gets the top performing stores in a specific region (e.g., 'Delhi NCR', 'Mumbai Metro') 
    for a given product super category and quarter.
    """
    query = f"""
    WITH quarter_dates AS (
        SELECT MIN(date) AS q_start, MAX(date) AS q_end FROM calendar WHERE quarter = '{quarter}'
    ),
    store_region AS (
        SELECT sgm.store_id, sgm.region_name
        FROM store_geo_mapping sgm
        CROSS JOIN quarter_dates qd
        WHERE sgm.effective_from <= CAST(qd.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(qd.q_start AS VARCHAR))
          AND sgm.region_name = '{region_name}'
    ),
    gross_revenue AS (
        SELECT oi.store_id, SUM(oi.line_total) AS gross_rev
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN products p ON oi.product_id = p.product_id
        CROSS JOIN quarter_dates qd
        WHERE o.order_status = 'completed' AND oi.is_cancelled = 0
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
          AND p.super_category_id = '{super_category_id}'
        GROUP BY oi.store_id
    ),
    returns_table AS (
        SELECT oi.store_id, SUM(r.refund_amount) AS refunds
        FROM returns r
        JOIN order_items oi ON r.order_item_id = oi.order_item_id
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON r.order_id = o.order_id
        CROSS JOIN quarter_dates qd
        WHERE r.refund_status = 'refunded'
          AND o.order_date >= qd.q_start AND o.order_date <= qd.q_end
          AND p.super_category_id = '{super_category_id}'
        GROUP BY oi.store_id
    )
    SELECT sr.region_name, gr.store_id, ROUND(gr.gross_rev - COALESCE(rt.refunds, 0), 2) AS net_revenue
    FROM store_region sr
    JOIN gross_revenue gr ON sr.store_id = gr.store_id
    LEFT JOIN returns_table rt ON sr.store_id = rt.store_id
    ORDER BY net_revenue DESC LIMIT 5;
    """
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute(query).fetchdf()
        con.close()
        return df.to_json(orient='records')
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- TOOL 2: Quarter-over-Quarter Trend ---
def get_qoq_trend(region_name: str) -> str:
    """
    Gets the quarter-over-quarter (QoQ) growth rate of net revenue for a specific region 
    (e.g., 'Delhi NCR', 'Mumbai Metro') over the last 6 quarters, including anomaly event flags.
    """
    query = f"""
    WITH target_quarters AS (
        SELECT DISTINCT quarter, MIN(date) as q_start, MAX(date) as q_end
        FROM calendar WHERE quarter <= '2026Q1' GROUP BY quarter ORDER BY quarter DESC LIMIT 7
    ),
    store_region AS (
        SELECT sgm.store_id, sgm.region_name, tq.quarter, tq.q_start, tq.q_end
        FROM store_geo_mapping sgm
        CROSS JOIN target_quarters tq
        WHERE sgm.effective_from <= CAST(tq.q_end AS VARCHAR)
          AND (sgm.effective_to IS NULL OR sgm.effective_to >= CAST(tq.q_start AS VARCHAR))
          AND sgm.region_name = '{region_name}'
    ),
    regional_events AS (
        SELECT DISTINCT tq.quarter, 1 AS has_event
        FROM store_events se
        CROSS JOIN target_quarters tq
        JOIN store_region sr ON se.store_id = sr.store_id AND sr.quarter = tq.quarter
        WHERE se.event_type IN ('flood_closure', 'strike', 'system_outage')
          AND se.start_date <= CAST(tq.q_end AS VARCHAR)
          AND (se.end_date IS NULL OR se.end_date >= CAST(tq.q_start AS VARCHAR))
    ),
    gross_revenue AS (
        SELECT oi.store_id, tq.quarter, SUM(oi.line_total) AS gross_rev
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        JOIN calendar c ON o.order_date = c.date
        JOIN target_quarters tq ON c.quarter = tq.quarter
        JOIN stores s ON oi.store_id = s.store_id
        WHERE o.order_status = 'completed' AND oi.is_cancelled = 0
          AND s.launch_date < tq.q_start
        GROUP BY oi.store_id, tq.quarter
    ),
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
    regional_revenue AS (
        SELECT sr.quarter, SUM(gr.gross_rev - COALESCE(rd.refunds, 0)) as net_revenue
        FROM store_region sr
        JOIN gross_revenue gr ON sr.store_id = gr.store_id AND sr.quarter = gr.quarter
        LEFT JOIN return_deductions rd ON sr.store_id = rd.store_id AND sr.quarter = rd.quarter
        GROUP BY sr.quarter
    )
    SELECT rr.quarter, ROUND(rr.net_revenue, 2) AS net_revenue,
           ROUND(((rr.net_revenue - LAG(rr.net_revenue) OVER(ORDER BY rr.quarter)) / LAG(rr.net_revenue) OVER(ORDER BY rr.quarter)) * 100, 2) AS qoq_growth_pct,
           CASE WHEN re.has_event = 1 THEN 'Yes' ELSE 'No' END AS event_impacted
    FROM regional_revenue rr
    LEFT JOIN regional_events re ON rr.quarter = re.quarter
    ORDER BY rr.quarter DESC LIMIT 6;
    """
    try:
        con = duckdb.connect(str(DB_PATH), read_only=True)
        df = con.execute(query).fetchdf()
        con.close()
        return df.to_json(orient='records')
    except Exception as e:
        return json.dumps({"error": str(e)})


# --- Streamlit UI Main App ---
def main():
    st.title("🛒 ZS Retail Intelligence Copilot")
    st.markdown("Ask natural language questions to interact with your DuckDB analytical engine.")
    
    # Initialize Gemini API
    api_key = os.environ.get("GEMINI_API_KEY", "AIzaSyBhlapE5SEoHek4dlwS_H9rCHhieX1vBPI")
    
    if "client" not in st.session_state:
        st.session_state.client = genai.Client(api_key=api_key)
        
    if "chat" not in st.session_state:
        config = types.GenerateContentConfig(
            tools=[get_store_performance, get_qoq_trend],
            system_instruction=(
                "You are the ZS Retail Intelligence Copilot. Your job is to answer business questions accurately using the provided tools."
                "1. NEVER guess or calculate metrics yourself. ALWAYS use the provided tools."
                "2. The valid regions are usually formatted like 'Delhi NCR', 'Mumbai Metro', 'Bengaluru Metro'."
                "3. ALWAYS cite the exact numbers returned by the tools."
                "4. If a tool indicates an event impacted the quarter, you MUST explicitly inform the user."
            ),
            temperature=0.0
        )
        st.session_state.chat = st.session_state.client.chats.create(model='gemini-2.5-flash', config=config)
        
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I am your AI Copilot. Ask me about **store performance** or **quarter-over-quarter trends** for any region."}
        ]

    # Display chat messages from history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Accept user input
    if prompt := st.chat_input("E.g., How did Delhi NCR perform in 2026Q1?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing retail data..."):
                try:
                    # Gemini automatically calls the Python tools when needed!
                    response = st.session_state.chat.send_message(prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"Error fetching data: {e}. (This could be a Gemini API timeout due to high traffic)")

if __name__ == "__main__":
    main()
