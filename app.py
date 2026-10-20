import streamlit as st
import pandas as pd
from datetime import time
import numpy as np
from calculations import financial_model_calculations
import plotly.express as px


st.title("Downtown Millbrae Financial Model Dashboard")
"This dashboard was created to simulate different financial scenarios for Millbrae. Not many assumptions were used to build this model, so results should be interpreted with caution and only used for general magnitudes."

with st.expander("Assumptions"):
    st.markdown("""
    1. Data was collected on:
        - Weekday: 5/4/23 (Thu)
        - Weekend: 5/6/23 (Sat)
    2. ULI Monthly factors were used to extrapolate data throughout the whole year (Same ULI factors were used from El Camino Financial Model)
    3. Certain parking lots were not captured. For these parking counts were collected using near maps and extrapolated for the year
    4. Assumed sessions that lasted longer than 2 hours on parking segments that are now assigned to 2h time limit parking are displaced to parking lots.
    5. Assumes that people who park 0-1 hrs, pay for 1hr and same logic follows for subsequent hours
    """)
    st.write("")

if "saved_scenarios" not in st.session_state:
    st.session_state.saved_scenarios = []   

with st.sidebar:
    st.header("Inputs")

    # 0. Input Scenario Name
    # scenario_name = st.text_input(
    #     "Scenario Name",
    #     placeholder="e.g. Baseline"
    #     )
    # 0. RPP mode
    RPP_mode = st.pills("RPP Mode", ["Existing","Expanded"], default="Existing")

    # 1. Parking Operator
    parking_operator = st.selectbox("Select a Parking Operator", ["LAZ","ACE"])

    # 2. Meter Type
    meter_type = st.selectbox("Select a Paystation Type", ["Multi-Space","Single-Space","Dual-Head"])
    
    # # 3. Rate and Hrs of Operation
    # wkdy_col, wkend_col = st.columns(2, border = True)

    # 3a. Weekday Inputs
    # with wkdy_col:
    # st.header("Weekday")
    # wkdy_offstreet_ = st.number_input("Cost of Parking ($/hr)", min_value=0.00, step=0.25)
    wkdy_start_time = st.time_input("Start Time", format = "12h", key="wkdy_start", value =time(10,0), step =3600)
    wkdy_end_time = st.time_input("End Time", format = "12h", key="wkdy_end", value =time(21,0), step =3600)
    wkdy_start_time = wkdy_start_time.hour
    wkdy_end_time = wkdy_end_time.hour

    wkend_start_time = wkdy_start_time
    wkend_end_time = wkdy_end_time
    # # 3b. Weekend Inputs
    # with wkend_col:
    #     st.header("Weekend")
    #     wkend_price_choice = st.number_input("test", min_value=0.00, step=0.25)
    #     wkend_start_time = st.time_input("Start Time", format = "12h", key="wkend_start", value =time(8,0), step =1800)
    #     wkend_end_time = st.time_input("End Time", format = "12h", key="wkend_end",value =time(18,0), step=1800)
    
    wkdy_hrly_rate = st.number_input("Parking Hourly Rate", value=1.50)
    wkend_hrly_rate = wkdy_hrly_rate
    wkdy_daily_rate = st.number_input("Parking Lot Day Rate", value=10)
    wkend_daily_rate = wkdy_daily_rate
    permit_rate = st.number_input("Monthly Permit Rate", value=50)
    # RPP Annual price
    rpp_price = st.number_input("Yearly RPP Rate", value=100)

    with st.expander("Advanced Settings"):

        # inflation = st.number_input("Inflation (%)", value=3)
        # inflation = inflation/100 + 1
        # yearly_revenue_increase = st.number_input("Yearly Revenue Increase (%)", value=0.5)
        # yearly_revenue_increase = yearly_revenue_increase/100 + 1
        attrition_rate = st.number_input("Attrition Rate (%/$)", value=0.15)
        time_range = st.radio("Time Range (years)", [3,5])
        sunday_parking_bool = st.checkbox("Enable Sunday Parking", value=False)

    if st.button("Save Scenario"):       
        scenario = {
            "Scenario": scenario_name,
            "Operator": parking_operator,
            "Meter Type": meter_type,
            # "Rate": price_choice,
            # "Year One Revenue": annual_revenue,
            # "Annual Expenses": annual_expenses,
            # "Net Revenue": net_revenue
        }

        st.session_state.saved_scenarios.append(scenario)

        st.success("Scenario saved!") 

with st.expander("Map"):
    st.map(latitude = 37.5991, longitude = -122.3995)
# st.subheader("Scenario Comparison")

# if st.session_state.saved_scenarios:

#     comparison_df = pd.DataFrame(
#         st.session_state.saved_scenarios
#     )

#     st.dataframe(
#         comparison_df,
#         hide_index=True,
#         width="stretch"
#     )

# else:
#     st.info("Save a scenario to begin comparing options.")

# if st.button("Clear Scenarios"):
#     st.session_state.saved_scenarios = []
#     st.rerun()

# CALCULATIONS
yearly_revenue_expenses = financial_model_calculations(parking_operator, RPP_mode, rpp_price, meter_type, time_range, sunday_parking_bool, attrition_rate, permit_rate, wkdy_hrly_rate, wkdy_daily_rate, wkdy_start_time, wkdy_end_time, wkend_hrly_rate,wkend_daily_rate, wkend_start_time, wkend_end_time)

# Summary Table
st.dataframe(yearly_revenue_expenses.set_index("Years"),column_config={
"Hrly Revenue": st.column_config.NumberColumn(format="dollar"),
"Daily Revenue": st.column_config.NumberColumn(format="dollar"),
"Permit Revenue": st.column_config.NumberColumn(format="dollar"),
"RPP Revenue" : st.column_config.NumberColumn(format="dollar"),
"Total Revenue": st.column_config.NumberColumn(format="dollar"),
"Enforcement Costs": st.column_config.NumberColumn(format="dollar"),
"Parking Mngmt Costs": st.column_config.NumberColumn(format="dollar"),
"CapEX": st.column_config.NumberColumn(format="dollar"),
"Total Expenses": st.column_config.NumberColumn(format="dollar"),
"Net Income": st.column_config.NumberColumn(format="dollar"),})

import plotly.graph_objects as go
revenue_cols = ["Hrly Revenue", "Daily Revenue", "Permit Revenue", "RPP Revenue"]
expense_cols = ["Enforcement Costs", "Parking Mngmt Costs", "CapEX"]
fig = go.Figure()

# Revenue components
for col in revenue_cols:
    fig.add_bar(
        x=yearly_revenue_expenses["Years"],
        y=yearly_revenue_expenses[col],
        name=col,
        offsetgroup="Revenue",
        legendgroup="Revenue"
    )

# Expense components
for col in expense_cols:
    fig.add_bar(
        x=yearly_revenue_expenses["Years"],
        y=yearly_revenue_expenses[col],
        name=col,
        offsetgroup="Expenses",
        legendgroup="Expenses"
    )

# Net Income labels
for _, row in yearly_revenue_expenses.iterrows():

    net_income = row["Net Income"]

    if net_income < 0:
        label = f'-${abs(net_income):,.0f}'
    else:
        label = f'${net_income:,.0f}'

    fig.add_annotation(
        x=row["Years"],
        y=max(row["Total Revenue"], row["Total Expenses"]),
        text=label,
        showarrow=False,
        yshift=15,
        font=dict(size=12)
    )

fig.update_layout(
    barmode="stack",
    yaxis_title="Amount ($)",
    xaxis_title="Year"
)

st.plotly_chart(fig, use_container_width=True)
