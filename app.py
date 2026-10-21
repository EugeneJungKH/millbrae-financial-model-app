"""
Downtown Millbrae Financial Model Dashboard

Purpose
-------
Interactive Streamlit dashboard used to test parking program scenarios
and estimate annual revenues, expenses, and net income.

The assumptions are stored separetly in:
    assumptions.md

The detailed financial calculations are stored separately in:
    calculations.py -> financial_model_calculations()

This file is primarily responsible for:
    1. Collecting user inputs
    2. Passing inputs to the financial model
    3. Displaying model results
    4. Visualizing revenue and expenses
"""

# import packages
import streamlit as st
import plotly.graph_objects as go
from datetime import time
from calculations import financial_model_calculations

# =============================================================================
# CONFIGURATION
# =============================================================================
DASHBOARD_TITLE = "Downtown Millbrae Financial Model Dashboard"
REVENUE_COLUMNS = [
    "Hrly Revenue",
    "Daily Revenue",
    "Permit Revenue",
    "RPP Revenue",
]
EXPENSE_COLUMNS = [
    "Enforcement Costs",
    "Parking Mngmt Costs",
    "CapEX",
]
CURRENCY_COLUMNS = REVENUE_COLUMNS + EXPENSE_COLUMNS + [
    "Total Revenue",
    "Total Expenses",
    "Net Income",
]
# =============================================================================
# PAGE HEADER
# =============================================================================
st.title(DASHBOARD_TITLE)
st.write(
    """
    This dashboard simulates different parking financial scenarios for
    Downtown Millbrae. The model relies on a limited number of assumptions,
    so results should be interpreted with caution and used primarily to
    understand the general magnitude of potential financial impacts.
    """
)
# =============================================================================
# MODEL ASSUMPTIONS
# =============================================================================
with open("assumptions.md", "r", encoding="utf-8") as file:
    assumptions = file.read()

with st.expander("Assumptions"):
    st.markdown(assumptions)

# =============================================================================
# SIDEBAR INPUTS
# =============================================================================
with st.sidebar:
    st.header("Scenario Inputs")

    # -------------------------------------------------------------------------
    # Parking Program
    # -------------------------------------------------------------------------
    st.subheader("Parking Program")

    rpp_mode = st.pills(
        "RPP Mode",
        options=["Existing", "Expanded"],
        default="Existing",
    )

    parking_operator = st.selectbox(
        "Parking Operator",
        options=["LAZ", "ACE", "In House"],
    )

    meter_type = st.selectbox(
        "Paystation Type",
        options=["Multi-Space", "Single-Space", "Dual-Head"],
    )

    # -------------------------------------------------------------------------
    # Parking Hours
    # -------------------------------------------------------------------------
    st.subheader("Hours of Operation")

    weekday_start_time = st.time_input(
        "Start Time",
        value=time(10, 0),
        format="12h",
        step=3600,
        key="weekday_start_time",
    )

    weekday_end_time = st.time_input(
        "End Time",
        value=time(21, 0),
        format="12h",
        step=3600,
        key="weekday_end_time",
    )

    # The financial model currently expects integer hours rather than
    # datetime.time objects.
    weekday_start_hour = weekday_start_time.hour
    weekday_end_hour = weekday_end_time.hour

    # Weekend hours currently use the same assumptions as weekdays.
    weekend_start_hour = weekday_start_hour
    weekend_end_hour = weekday_end_hour

    # -------------------------------------------------------------------------
    # Parking Rates
    # -------------------------------------------------------------------------
    st.subheader("Parking Rates")

    weekday_hourly_rate = st.number_input(
        "Parking Hourly Rate ($/hr)",
        min_value=0.00,
        value=1.50,
        step=0.25,
    )

    weekday_daily_rate = st.number_input(
        "Parking Lot Daily Rate ($/day)",
        min_value=0.00,
        value=10.00,
        step=1.00,
    )

    permit_rate = st.number_input(
        "Monthly Permit Rate ($/month)",
        min_value=0.00,
        value=50.00,
        step=5.00,
    )

    rpp_price = st.number_input(
        "Annual RPP Rate ($/year)",
        min_value=0.00,
        value=50.00,
        step=5.00,
    )

    # Weekend parking rates currently use the same assumptions as weekdays.
    weekend_hourly_rate = weekday_hourly_rate
    weekend_daily_rate = weekday_daily_rate

    # -------------------------------------------------------------------------
    # Advanced Settings
    # -------------------------------------------------------------------------

    with st.expander("Advanced Settings"):

        attrition_rate = st.number_input(
            "Attrition Rate (% per $1 increase)",
            value=0.15,
        )

        time_range = st.radio(
            "Analysis Period (years)",
            options=[3, 5],
        )

        sunday_parking_enabled = st.checkbox(
            "Enable Sunday Parking",
            value=False,
        )

# =============================================================================
# MAP
# =============================================================================

# Parking space allocation map
with st.expander("Parking Space Allocation Map"):
    st.image(r"data/11x17 RFP 061026_Page_1.png",use_container_width=True)

# Parking space allocation map
with st.expander("Residential Parking Permit Map"):
    st.image(r"data/11x17 RFP 061026_Page_3.png",use_container_width=True)

# =============================================================================
# RUN FINANCIAL MODEL
# =============================================================================

yearly_results = financial_model_calculations(
    parking_operator,
    rpp_mode,
    rpp_price,
    meter_type,
    time_range,
    sunday_parking_enabled,
    attrition_rate,
    permit_rate,
    weekday_hourly_rate,
    weekday_daily_rate,
    weekday_start_hour,
    weekday_end_hour,
    weekend_hourly_rate,
    weekend_daily_rate,
    weekend_start_hour,
    weekend_end_hour,
)


# =============================================================================
# RESULTS TABLE
# =============================================================================

st.subheader("Financial Summary")

column_configuration = {
    column: st.column_config.NumberColumn(format="dollar")
    for column in CURRENCY_COLUMNS
}

st.dataframe(
    yearly_results.set_index("Years"),
    column_config=column_configuration,
    use_container_width=True,
)


# =============================================================================
# REVENUE AND EXPENSE CHART
# =============================================================================

st.subheader("Annual Revenue and Expenses")

fig = go.Figure()


# Add stacked revenue components.
for column in REVENUE_COLUMNS:

    fig.add_bar(
        x=yearly_results["Years"],
        y=yearly_results[column],
        name=column,
        offsetgroup="Revenue",
        legendgroup="Revenue",
    )


# Add stacked expense components.
for column in EXPENSE_COLUMNS:

    fig.add_bar(
        x=yearly_results["Years"],
        y=yearly_results[column],
        name=column,
        offsetgroup="Expenses",
        legendgroup="Expenses",
    )


# Add net income above each year's bars.
for _, row in yearly_results.iterrows():

    net_income = row["Net Income"]

    if net_income < 0:
        net_income_label = f"-${abs(net_income):,.0f}"
    else:
        net_income_label = f"${net_income:,.0f}"

    fig.add_annotation(
        x=row["Years"],
        y=max(
            row["Total Revenue"],
            row["Total Expenses"],
        ),
        text=net_income_label,
        showarrow=False,
        yshift=15,
        font=dict(size=12),
    )


fig.update_layout(
    barmode="stack",
    xaxis_title="Year",
    yaxis_title="Amount ($)",
)


st.plotly_chart(
    fig,
    use_container_width=True,
)