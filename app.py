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
from calculationv2 import financial_model_calculations
from excel_export import build_excel_file


# =============================================================================
# PAGE HEADER
# =============================================================================
st.title("Downtown Millbrae Financial Model Dashboard")
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

    weekday_onstreet_hourly_rate = st.number_input(
        "On-Street Hourly Rate ($/hr)",
        min_value=0.00,
        value=1.00,
        step=0.25,
    )

    weekday_offstreet_hourly_rate = st.number_input(
        "Off-Street Hourly Rate ($/hr)",
        min_value=0.00,
        value=1.00,
        step=0.25,
    )

    # The daily maximum is derived from the off-street hourly rate.
    DAILY_MAX_MULTIPLIER = 4
    weekday_daily_rate = DAILY_MAX_MULTIPLIER * weekday_offstreet_hourly_rate

    st.caption(
        f"Off-street daily maximum: ${weekday_daily_rate:,.2f}/day "
        f"({DAILY_MAX_MULTIPLIER}x the off-street hourly rate)"
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
    weekend_onstreet_hourly_rate = weekday_onstreet_hourly_rate
    weekend_offstreet_hourly_rate = weekday_offstreet_hourly_rate
    weekend_daily_rate = weekday_daily_rate

    # -------------------------------------------------------------------------
    # Advanced Settings
    # -------------------------------------------------------------------------

    with st.expander("Advanced Settings"):

        attrition_rate = st.number_input(
            "Attrition Rate (% per $1 increase)",
            value=15,
        )

        inhouse_scaling_factor = st.number_input(
                    "In House Scaling Factor (%)",
                    value=5,
                )
        inhouse_scaling_factor = 1 + (inhouse_scaling_factor / 100)

        # convert attrition rate from percentage to decimal
        attrition_rate = attrition_rate / 100

        time_range = st.radio(
            "Analysis Period (years)",
            options=[3, 5],
        )

        sunday_parking_enabled = st.checkbox(
            "Enable Sunday Parking",
            value=False,
        )

        credit_card_processing_fee = st.checkbox(
            "Enable Credit Card Processing Fee",
            value=False,
        )

        credit_card_percentage = 0

        if credit_card_processing_fee:
            credit_card_percentage = st.number_input(
                "Percent of Transactions Made With Credit Card (%)",
                value=50,
            )
            credit_card_percentage = credit_card_percentage / 100

# =============================================================================
# CONFIGURATION
# =============================================================================
REVENUE_COLUMNS = [
    "Citation Revenue",
    "Hrly Revenue",
    "Daily Revenue",
    "Permit Revenue",
    "RPP Revenue",
]
EXPENSE_COLUMNS = [
    "Citation Expenses",
    "Enforcement Costs",
    "Parking Mngmt Costs",
    "CapEX",
    "Credit Card Processing Fee",
]

# add credit card processing fee to the list of expense columns if enable credit card processing fee is selected
if not credit_card_processing_fee:
    EXPENSE_COLUMNS.remove("Credit Card Processing Fee")

CURRENCY_COLUMNS = REVENUE_COLUMNS + EXPENSE_COLUMNS + [
    "Total Revenue",
    "Total Expenses",
    "Net Income",
]
# Streamlit's default light theme chart colors, used for the Excel chart.
COLUMN_COLORS = {
    "Hrly Revenue": "#0068C9",
    "Daily Revenue": "#83C9FF",
    "Permit Revenue": "#FF2B2B",
    "RPP Revenue": "#FFABAB",
    "Citation Revenue": "#bfef45",
    "Enforcement Costs": "#29B09D",
    "Parking Mngmt Costs": "#7DEFA1",
    "CapEX": "#FF8700",
    "Citation Expenses": "#911eb4",
    "Credit Card Processing Fee": "#FF69B4",
}

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
    weekday_onstreet_hourly_rate,
    weekday_offstreet_hourly_rate,
    weekday_daily_rate,
    weekday_start_hour,
    weekday_end_hour,
    weekend_onstreet_hourly_rate,
    weekend_offstreet_hourly_rate,
    weekend_daily_rate,
    weekend_start_hour,
    weekend_end_hour,
    inhouse_scaling_factor,
    credit_card_processing_fee,
    credit_card_percentage
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
        yshift=40,
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
# Download Button
# =============================================================================

st.download_button(
    "Download Excel File",
    data=build_excel_file(
        yearly_results,
        REVENUE_COLUMNS,
        EXPENSE_COLUMNS,
        CURRENCY_COLUMNS,
        COLUMN_COLORS,
        parking_operator,
        rpp_mode,
        meter_type,
        weekday_start_hour,
        weekday_end_hour,
        weekday_onstreet_hourly_rate,
        weekday_offstreet_hourly_rate,
        permit_rate,
        rpp_price,
        attrition_rate,
        inhouse_scaling_factor,
        time_range,
        sunday_parking_enabled,
        credit_card_processing_fee,
        credit_card_percentage,
    ),
    file_name="Millbrae Financial Model Export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)