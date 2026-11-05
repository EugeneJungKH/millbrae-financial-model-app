"""
Downtown Millbrae Parking Financial Model - Calculations

This file is used for the financial calculation in the Downtown Millbrae Parking Financial Model. It calculates parking demand, annual revenue, expenses, and net income for
different parking-management scenarios.

"""

# import packages
from pathlib import Path
import numpy as np
import pandas as pd
import numpy_financial as npf

"""
=============================================================================
FUNCTION 1. ADJUST DEMAND BASED ON TIME OF DAY
=============================================================================
"""

# read in ULI TOD adjustment factors
demand_distribution = pd.read_excel(r"data/ULI Factors.xlsx", sheet_name="TOD Adjustments")

def adjust_demand_for_time_of_day(start_time, end_time, demand, day_type):
    """Adjust observed parking demand (10 AM-8 PM) to the selected paid parking hours using ULI time-of-day factors."""

    # Original data collection period
    data_collection_start = 10  # 10 AM
    data_collection_end = 20    # 8 PM

    # Calculate demand factor for original data collection period
    base_period = demand_distribution[(demand_distribution["TOD"] >= data_collection_start) & (demand_distribution["TOD"] <= data_collection_end)]
    base_demand_factor = base_period[f"{day_type} Normalized TOD Demand"].sum()

    # Calculate demand factor for selected paid parking period
    selected_period = demand_distribution[(demand_distribution["TOD"] >= start_time) & (demand_distribution["TOD"] <= end_time)]
    selected_demand_factor = selected_period[f"{day_type} Normalized TOD Demand"].sum()

    # Adjust demand based on difference between the two periods
    adjusted_demand = demand * (selected_demand_factor / base_demand_factor)

    return adjusted_demand

"""
=============================================================================
FUNCTION 2. MAIN CALCULATIONS
=============================================================================
"""

def financial_model_calculations(parking_operator, RPP_mode, rpp_price, meter_type, time_range, sunday_parking_bool, attrition_rate, permit_rate, 
                                 wkdy_onstreet_hrly_rate, wkdy_offstreet_hrly_rate, wkdy_daily_rate, wkdy_start_time, wkdy_end_time,
                                 wkend_onstreet_hrly_rate, wkend_offstreet_hrly_rate, wkend_daily_rate, wkend_start_time, wkend_end_time, inhouse_scaling_factor):
    # read in raw count data
    raw_counts_df = pd.read_excel(r"data/Segments Pricing Calculations 06192024.xlsx", sheet_name="Raw")

    # filter raw_count_df to only include below columns
    counts_column_list = [ "Segment", "TO_Sat_0-1 HRS", "TO_Sat_1-2 HRS","TO_Sat_2-3 HRS","TO_Sat_3-4 HRS","TO_Sat_4-5 HRS", "TO_Sat_5-6 HRS",
        "TO_Sat_6-7 HRS","TO_Sat_7-8 HRS","TO_Sat_8-9 HRS","TO_Sat_9-10 HRS","TO_Thu_0-1 HRS","TO_Thu_1-2 HRS",
        "TO_Thu_2-3 HRS","TO_Thu_3-4 HRS","TO_Thu_4-5 HRS","TO_Thu_5-6 HRS","TO_Thu_6-7 HRS","TO_Thu_7-8 HRS","TO_Thu_8-9 HRS",
        "TO_Thu_9-10 HRS"]
    counts_df = raw_counts_df[counts_column_list]

    # group counts_df based on segment key type
    segment_key_df = pd.read_csv(r"data/segment_key.csv") # this df lists which segments are 2h vs lot vs zone a
    counts_df = counts_df.merge(segment_key_df[["Segment","park_type"]], left_on="Segment",right_on="Segment") # merge key df with count_df
    key_counts_df = counts_df.drop(columns=["Segment"]).groupby("park_type").sum().T.reset_index() # group data by key


    # split the index for easier reference
    key_counts_df[["Turnover","DOW","Duration"]] = key_counts_df["index"].str.split(pat="_", expand = True)
    key_counts_df = key_counts_df.drop(columns=["Proposed Zone A", "Zone A", "Zone A/C", "Zone C", "Turnover"])
    # add column for avg duration parked
    key_counts_df["hrs_parked"] = [0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5]

    # =============================================================================
    """
    1. PERMIT PARKERS
    """

    # Find number of permit parkers (people who park longer than 6 hours)
    thu_permit_count = key_counts_df[key_counts_df["DOW"] == "Thu"][key_counts_df["hrs_parked"] > 6][["All Day","2h","2h Free","Lot"]].sum(numeric_only=True).sum()
    sat_permit_count = key_counts_df[key_counts_df["DOW"] == "Sat"][key_counts_df["hrs_parked"] > 6][["All Day","2h","2h Free","Lot"]].sum(numeric_only=True).sum()
    # choose more conservative estimate for permit parkers
    permit_count = min(sat_permit_count, thu_permit_count)
    # adjust the permit count assuming 80% of workers are present on thursday
    permit_count_adjusted = round(permit_count / 0.8)


    # =============================================================================
    """
    1. Adjust demand based on enforcement hours
    """
    key_counts_adj_df = key_counts_df.copy()

    key_counts_adj_df["All Day"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, key_counts_adj_df["All Day"], "Weekday")
    key_counts_adj_df["2h"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, key_counts_adj_df["2h"], "Weekday" )
    key_counts_adj_df["2h Free"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, key_counts_adj_df["2h Free"], "Weekday")
    key_counts_adj_df["Lot"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, key_counts_adj_df["Lot"], "Weekday")

    # =============================================================================
    """
    2. DAILY PARKERS
    """
    # split key_counts_adj into thu and sat df for convenience
    key_counts_adj_df_thu = key_counts_adj_df[key_counts_adj_df["DOW"] == "Thu"]
    key_counts_adj_df_sat = key_counts_adj_df[key_counts_adj_df["DOW"] == "Sat"]

    # calculate the daily user counts (for certain classifications its people who parked 4-6 hours, and for 2h its people who parked 2-6 hours)
    thu_daily_count = key_counts_adj_df_thu[["All Day","2h Free","Lot"]][(key_counts_adj_df_thu["hrs_parked"] > 4)&(key_counts_adj_df_thu["hrs_parked"] <= 6)].sum(numeric_only=True).sum() + key_counts_adj_df_thu["2h"][(key_counts_adj_df_thu["hrs_parked"] > 2)&(key_counts_adj_df_thu["hrs_parked"] <= 6)].sum(numeric_only=True).sum()
    sat_daily_count = key_counts_adj_df_sat[["All Day","2h Free","Lot"]][(key_counts_adj_df_sat["hrs_parked"] > 4)&(key_counts_adj_df_sat["hrs_parked"] <= 6)].sum(numeric_only=True).sum() + key_counts_adj_df_sat["2h"][(key_counts_adj_df_sat["hrs_parked"] > 2)&(key_counts_adj_df_sat["hrs_parked"] <= 6)].sum(numeric_only=True).sum()

    # apply attrition to count and caluclate revenue
    thu_daily_revenue = thu_daily_count * max(0,1-attrition_rate*wkdy_onstreet_hrly_rate) * wkdy_daily_rate
    sat_daily_revenue = sat_daily_count * max(0,1-attrition_rate*wkend_onstreet_hrly_rate) * wkend_daily_rate

    # =============================================================================
    """
    2. HRLY PARKERS
    """
    # create a copy of the key_coutns table that is in veh-hrs instead of counts
    key_veh_hrs_adj_df = key_counts_adj_df.copy()
    key_veh_hrs_adj_df["All Day"] = key_veh_hrs_adj_df["All Day"] * key_veh_hrs_adj_df["hrs_parked"]
    key_veh_hrs_adj_df["2h"] = key_veh_hrs_adj_df["2h"] * key_veh_hrs_adj_df["hrs_parked"]
    key_veh_hrs_adj_df["2h Free"] = key_veh_hrs_adj_df["2h Free"] * key_veh_hrs_adj_df["hrs_parked"]
    key_veh_hrs_adj_df["Lot"] = key_veh_hrs_adj_df["Lot"] * key_veh_hrs_adj_df["hrs_parked"]

    # split that table into weekend and weekday for conveneince
    key_veh_hrs_adj_df_thu = key_veh_hrs_adj_df[key_veh_hrs_adj_df["DOW"] == "Thu"]
    key_veh_hrs_adj_df_sat = key_veh_hrs_adj_df[key_veh_hrs_adj_df["DOW"] == "Sat"]

    # find the veh_hrs for the data - seperate for offstreet and on street parking
    thu_hrly_veh_hrs_lot = (
                        key_veh_hrs_adj_df_thu["Lot"][key_veh_hrs_adj_df_thu["hrs_parked"] < 4].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_thu["2h Free"][(key_veh_hrs_adj_df_thu["hrs_parked"] > 2)&(key_veh_hrs_adj_df_thu["hrs_parked"] < 4)].sum(numeric_only=True).sum() 
                        )

    thu_hrly_veh_hrs_street = (
                        key_veh_hrs_adj_df_thu[["All Day","Lot"]][key_veh_hrs_adj_df_thu["hrs_parked"] < 4].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_thu["2h"][key_veh_hrs_adj_df_thu["hrs_parked"] < 2].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_thu["2h Free"][(key_veh_hrs_adj_df_thu["hrs_parked"] > 2)&(key_veh_hrs_adj_df_thu["hrs_parked"] < 4)].sum(numeric_only=True).sum() 
                        )

    sat_hrly_veh_hrs_lot = (
                        key_veh_hrs_adj_df_sat["Lot"][key_veh_hrs_adj_df_sat["hrs_parked"] < 4].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_sat["2h Free"][(key_veh_hrs_adj_df_sat["hrs_parked"] > 2)&(key_veh_hrs_adj_df_sat["hrs_parked"] < 4)].sum(numeric_only=True).sum() 
                        )

    sat_hrly_veh_hrs_street = (
                        key_veh_hrs_adj_df_sat[["All Day","Lot"]][key_veh_hrs_adj_df_sat["hrs_parked"] < 4].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_sat["2h"][key_veh_hrs_adj_df_sat["hrs_parked"] < 2].sum(numeric_only=True).sum() 
                        + key_veh_hrs_adj_df_sat["2h Free"][(key_veh_hrs_adj_df_sat["hrs_parked"] > 2)&(key_veh_hrs_adj_df_sat["hrs_parked"] < 4)].sum(numeric_only=True).sum() 
                        )

    # apply attrition and calculate revenue
    thu_hrly_revenue_lot = thu_hrly_veh_hrs_lot * max(0,1-attrition_rate*wkdy_offstreet_hrly_rate) * wkdy_offstreet_hrly_rate
    thu_hrly_revenue_street = thu_hrly_veh_hrs_street * max(0,1-attrition_rate*wkdy_onstreet_hrly_rate) * wkdy_onstreet_hrly_rate

    sat_hrly_veh_hrs_lot = sat_hrly_veh_hrs_lot * max(0,1-attrition_rate*wkdy_offstreet_hrly_rate) * wkdy_offstreet_hrly_rate
    sat_hrly_veh_hrs_street = sat_hrly_veh_hrs_street * max(0,1-attrition_rate*wkdy_onstreet_hrly_rate) * wkdy_onstreet_hrly_rate

    # calculate total revenues
    thu_hrly_revenue = thu_hrly_revenue_lot + thu_hrly_revenue_street
    sat_hrly_revenue = sat_hrly_veh_hrs_lot + sat_hrly_veh_hrs_street

    # =============================================================================
    """
    2. Calculate Revenue
    """

    # Hrly Parkers revenue
    ULI_df = pd.read_excel(r"data/ULI Factors.xlsx") # read in ULI Factors
    hrly_revenue_yr = ((thu_hrly_revenue * 5/7 + sat_hrly_revenue * (sunday_parking_bool + 1)/7) * ULI_df["Days in the Month"] * ULI_df["Multiplying Factor"]).sum()

    # Daily Revenue
    daily_revenue_yr = ((thu_daily_revenue * 5/7 + sat_daily_revenue * (sunday_parking_bool + 1)/7) * ULI_df["Days in the Month"] * ULI_df["Multiplying Factor"]).sum()

    # Permit Parkers revenue
    permit_revenue_yr = permit_count_adjusted * permit_rate * 12

    # Citation Revenue
    citation_revenue_yr = 171807.62 # based on real data

    # RPP Revenue
    if RPP_mode == "Existing":
        RPP_revenue_yr = rpp_price * 878 # 878 is the current amount of RPP users
    elif RPP_mode == "Expanded":
        RPP_revenue_yr = rpp_price * 878/956 * 1489 # use same % of active RPP households * total households

    # organize revenue into a table
    beginning_year = 2027
    years = np.arange(beginning_year,beginning_year+time_range,1) 
    yearly_revenue_expenses = pd.DataFrame()
    yearly_revenue_expenses["Years"] = years
    year_index = np.arange(time_range)
    yearly_revenue_expenses["Hrly Revenue"] = hrly_revenue_yr
    yearly_revenue_expenses["Daily Revenue"] = daily_revenue_yr
    yearly_revenue_expenses["Permit Revenue"] = permit_revenue_yr
    yearly_revenue_expenses["Citation Revenue"] = citation_revenue_yr
    yearly_revenue_expenses["RPP Revenue"] = RPP_revenue_yr

    yearly_revenue_expenses["Total Revenue"] = hrly_revenue_yr + daily_revenue_yr + permit_revenue_yr + citation_revenue_yr + RPP_revenue_yr


    # =============================================================================
    """
    2. Calculate Expenses
    """
    # read in expenses df


    if parking_operator == "In House":
        # read in sheet with expenses for LAZ and ACE
        expenses_df = pd.read_excel(r"data/Expenses.xlsx", sheet_name="In House")
        # select expense that matches user-chosen scenario
        expense_scenario = expenses_df[(expenses_df["RPP Scenario"] ==RPP_mode)&(expenses_df["Parking Provider"] ==parking_operator)&(expenses_df["Parking Meter Type"] ==meter_type)]
        # find enforcement cost
        enforcement_cost = expense_scenario["Enforcement Non Scaled Costs"].iloc[0] + expense_scenario["Enforcement Scaled Costs"].iloc[0] * inhouse_scaling_factor
        # find parking management cost
        parking_mgmt_cost = expense_scenario["Parking Management Non Scaled Costs"].iloc[0] + expense_scenario["Parking Management Scaled Costs"].iloc[0] * inhouse_scaling_factor
        # find capital cost
        capital_cost = expense_scenario["Cap Ex Non Scaled Costs"].iloc[0] + expense_scenario["Cap Ex Scaled Costs"].iloc[0] * inhouse_scaling_factor
        # convert capital costs to annualized costs using npf.pmt
        if time_range == 3:
            yearly_revenue_expenses["CapEX"] = -npf.pmt(0.10, 5, capital_cost)
        if time_range == 5:
            yearly_revenue_expenses["CapEX"] = -npf.pmt(0.10, 5, capital_cost)
    else:
        # read in sheet with expenses for LAZ and ACE
        expenses_df = pd.read_excel(r"data/Expenses.xlsx", sheet_name="LAZ-ACE")
        # select expense that matches user-chosen scenario
        expense_scenario = expenses_df[(expenses_df["RPP Scenario"] ==RPP_mode)&(expenses_df["Parking Provider"] ==parking_operator)&(expenses_df["Parking Meter Type"] ==meter_type)]
        # calculate enforcement cost
        enforcement_cost = expense_scenario["Enforcement Cost"].iloc[0]
        # find parking management cost
        parking_mgmt_cost = expense_scenario["Parking Management Cost"].iloc[0]
        # find capital cost
        if time_range == 3:
            yearly_revenue_expenses["CapEX"] = expense_scenario[r"Cap Ex Amoritized, 10% over 3 yrs"].iloc[0]
        elif time_range == 5:
            yearly_revenue_expenses["CapEX"] = expense_scenario[r"Cap Ex Amoritized, 10% over 5 yrs"].iloc[0]

    # adjust enforcement cost based on if sunday parking is allowed
    if (sunday_parking_bool == True)&(RPP_mode == "Existing"):
        enforcement_cost = enforcement_cost * 152/144
    elif (sunday_parking_bool == True)&(RPP_mode == "Expanded"):
        enforcement_cost = enforcement_cost * 200/192

    # calculate year of year increase
    yoy_increase = expense_scenario["YOY Increase"].iloc[0] + 1

    # citation cost (from real world data)
    citation_cost = 19090.15 # this is static and based on real data

    # add costs to df
    yearly_revenue_expenses["Enforcement Costs"] = (enforcement_cost* (yoy_increase ** year_index))
    yearly_revenue_expenses["Parking Mngmt Costs"] = (parking_mgmt_cost * (yoy_increase ** year_index))
    yearly_revenue_expenses["Citation Expenses"] = (citation_cost * (yoy_increase ** year_index))

    # calculate total expense and net income
    yearly_revenue_expenses["Total Expenses"] = yearly_revenue_expenses["Enforcement Costs"] + yearly_revenue_expenses["Parking Mngmt Costs"] + yearly_revenue_expenses["CapEX"] + yearly_revenue_expenses["Citation Expenses"]
    yearly_revenue_expenses["Net Income"] = yearly_revenue_expenses["Total Revenue"] - yearly_revenue_expenses["Total Expenses"]

    return yearly_revenue_expenses