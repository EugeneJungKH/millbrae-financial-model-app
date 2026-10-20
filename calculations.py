import pandas as pd
import numpy as np

# Functions to adjust demand based on time of day
def adjust_demand_for_time_of_day(start_time, end_time, demand, weekdayorweekend):
    # Inputs:
        # start_time: the start time of paid parking
        # end_time: the end time of paid parking
        # demand: series with demand
        # weekdayorweekend: indicator for whether the demand is for a weekday or weekend
    # Constants
        # demand_distribution: distribution of demand across a 24 hour period
    # Outputs:
        # adjusted_demand: the demand adjusted for the time of day

    demand_distribution = pd.read_excel(r"data\ULI Factors.xlsx", sheet_name="TOD Adjustments")
    # calculate TOD factor for the base data
    data_collection_start_time = 10 #10am
    data_collection_end_time = 20 #8pm
    # filter TOD factor so it only includes data from data collection start time to end time
    data_collection_distribution = demand_distribution[(demand_distribution["TOD"] >= data_collection_start_time)&(demand_distribution["TOD"] <= data_collection_end_time)]
    # add up to get the base data TOD factor 
    base_data_TOD_factor = data_collection_distribution[f"{weekdayorweekend} Normalized TOD Demand"].sum()

    # calculate TOD factor for user input time range
    user_input_distribution = demand_distribution[(demand_distribution["TOD"] >= start_time)&(demand_distribution["TOD"] <= end_time)]
    user_input_TOD_factor = user_input_distribution[f"{weekdayorweekend} Normalized TOD Demand"].sum()

    # calculate the demand for the user input time range
    adjusted_demand = demand * (user_input_TOD_factor / base_data_TOD_factor)

    # return the adjusted demand
    return adjusted_demand

def split_demand(hrs_parked,series,split_1,split_2):
    split_series = pd.Series()
    split_series.loc["Hrly"] = series.loc[hrs_parked <= split_1].sum()
    split_series.loc["Daily"] = series.loc[(hrs_parked > split_1)&(hrs_parked <= split_2)].sum()
    return split_series



def financial_model_calculations(parking_operator, RPP_mode, rpp_price, meter_type, time_range, sunday_parking_bool, attrition_rate, permit_rate, 
                                 wkdy_hrly_rate, wkdy_daily_rate, wkdy_start_time, wkdy_end_time, 
                                 wkend_hrly_rate,wkend_daily_rate, wkend_start_time, wkend_end_time):
    seg_TO_col = [
    "Segment",
    "TO_Sat_0-1 HRS",
    "TO_Sat_1-2 HRS",
    "TO_Sat_2-3 HRS",
    "TO_Sat_3-4 HRS",
    "TO_Sat_4-5 HRS",
    "TO_Sat_5-6 HRS",
    "TO_Sat_6-7 HRS",
    "TO_Sat_7-8 HRS",
    "TO_Sat_8-9 HRS",
    "TO_Sat_9-10 HRS",
    "TO_Thu_0-1 HRS",
    "TO_Thu_1-2 HRS",
    "TO_Thu_2-3 HRS",
    "TO_Thu_3-4 HRS",
    "TO_Thu_4-5 HRS",
    "TO_Thu_5-6 HRS",
    "TO_Thu_6-7 HRS",
    "TO_Thu_7-8 HRS",
    "TO_Thu_8-9 HRS",
    "TO_Thu_9-10 HRS"]

    # FORMAT DATA

    # read in segment data with parking duration data
    seg_TO = pd.read_excel(r"data\Segments Pricing Calculations 06192024.xlsx", sheet_name="Raw")
    # read in segment key data that tells the type of parking each segment is
    seg_key = pd.read_csv(r"data\segment_key.csv")
    # merge key data with segment data
    seg_TO = seg_TO.merge(right = seg_key[["Segment","park_type"]], left_on = "Segment", right_on = "Segment")

    # clean data
    seg_TO_clean = seg_TO[seg_TO_col]
    # merge data with key to know zoning/ classificatoin
    seg_TO_key = seg_TO_clean.merge(seg_key[["Segment","park_type"]], left_on="Segment",right_on="Segment")
    # group data
    seg_TO_sum = seg_TO_key.drop(columns=["Segment"]).groupby("park_type").sum().T.reset_index()

    # create column for hrs parked
    seg_TO_sum["hrs_parked"] = [0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,0.5,1.5,2.5,3.5,4.5,5.5,6.5,7.5,8.5,9.5,]

    # split the index for easier reference
    seg_TO_sum[["Turnover","DOW","length"]] = seg_TO_sum["index"].str.split(pat="_", expand = True)

    # reorganize columns for easier reference
    seg_TO_sum_clean = seg_TO_sum.copy()[["DOW","length","hrs_parked","All Day","2h","2h Free", "Lot"]]
    seg_TO_sum_clean

    # Find the number of permit parkers

    # assume anyone parking for more than 6 hours is a permit parker
    seg_TO_sum_clean_lots = seg_TO_sum_clean[seg_TO_sum_clean["hrs_parked"]>6]

    # calculate the number of people parking more than 6 hours for weekday and weekend
    sat_permit_count = seg_TO_sum_clean_lots[seg_TO_sum_clean_lots["DOW"] == "Sat"][["All Day","2h","2h Free","Lot"]].sum(numeric_only=True).sum()
    thu_permit_count = seg_TO_sum_clean_lots[seg_TO_sum_clean_lots["DOW"] == "Thu"][["All Day","2h","2h Free","Lot"]].sum(numeric_only=True).sum()

    # choose more conservative estimate for permit parkers
    permit_count = min(sat_permit_count, thu_permit_count)

    # adjust the permit count assuming 80% of workers are present on thhursday
    permit_count_adjusted = round(permit_count / 0.8)
    permit_count_adjusted
    
    # adjust demand based on time

    #create weekend and weekday df
    wkdy_df = seg_TO_sum_clean.copy()[seg_TO_sum_clean["DOW"] == "Thu"]
    wkend_df = seg_TO_sum_clean.copy()[seg_TO_sum_clean["DOW"] == "Sat"]

    # apply adjust_demand_for_time_of_day function to "All Day","2h","2h Free","Lot" columns
    wkdy_df["All Day TOD_Adj"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, wkdy_df["All Day"], "Weekday") * wkdy_df["hrs_parked"]
    wkdy_df["2h TOD_Adj"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, wkdy_df["2h"], "Weekday" )* wkdy_df["hrs_parked"]
    wkdy_df["2h Free TOD_Adj"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, wkdy_df["2h Free"], "Weekday") * wkdy_df["hrs_parked"]
    wkdy_df["Lot TOD_Adj"] = adjust_demand_for_time_of_day(wkdy_start_time, wkdy_end_time, wkdy_df["Lot"], "Weekday") * wkdy_df["hrs_parked"]

    # repeat for weekend
    wkend_df["All Day TOD_Adj"] = adjust_demand_for_time_of_day(wkend_start_time, wkend_end_time, wkend_df["All Day"], "Weekend") * wkend_df["hrs_parked"]
    wkend_df["2h TOD_Adj"] = adjust_demand_for_time_of_day(wkend_start_time, wkend_end_time, wkend_df["2h"], "Weekend") * wkend_df["hrs_parked"]
    wkend_df["2h Free TOD_Adj"] = adjust_demand_for_time_of_day(wkend_start_time, wkend_end_time, wkend_df["2h Free"], "Weekend") * wkend_df["hrs_parked"]
    wkend_df["Lot TOD_Adj"] = adjust_demand_for_time_of_day(wkend_start_time, wkend_end_time, wkend_df["Lot"], "Weekend") * wkend_df["hrs_parked"]

    # create an additional lot that captures people who parked over 2 hrs in 2h and 2h free
    wkdy_df["Lot >2h"] = wkdy_df["2h TOD_Adj"] + wkdy_df["2h Free TOD_Adj"]
    wkend_df["Lot >2h"] = wkend_df["2h TOD_Adj"] + wkend_df["2h Free TOD_Adj"]

    # set the first two hours of lot >2h to 0
    wkdy_df.iloc[:2, wkdy_df.columns.get_loc("Lot >2h")] = 0
    wkend_df.iloc[:2, wkend_df.columns.get_loc("Lot >2h")] = 0

    # create a new data frame with hrly, daily, or permit as rows
    wkdy_park_type_df = pd.DataFrame()

    # calculate all the All Day TOD_Adj revenue for each parking type
    wkdy_park_type_df["All Day"] = split_demand(wkdy_df["hrs_parked"], wkdy_df["All Day TOD_Adj"], 4, 6)
    wkdy_park_type_df["2h"] = split_demand(wkdy_df["hrs_parked"], wkdy_df["2h TOD_Adj"], 2, 6)
    wkdy_park_type_df["Lot"] = split_demand(wkdy_df["hrs_parked"], wkdy_df["Lot TOD_Adj"], 4, 6)
    wkdy_park_type_df["Lot >2h"] = split_demand(wkdy_df["hrs_parked"], wkdy_df["Lot >2h"], 4, 6)

    # repeat for weekend
    wkend_park_type_df = pd.DataFrame()
    wkend_park_type_df["All Day"] = split_demand(wkend_df["hrs_parked"], wkend_df["All Day TOD_Adj"], 4, 6)
    wkend_park_type_df["2h"] = split_demand(wkend_df["hrs_parked"], wkend_df["2h TOD_Adj"], 2, 6)
    wkend_park_type_df["Lot"] = split_demand(wkend_df["hrs_parked"], wkend_df["Lot TOD_Adj"], 4, 6)
    wkend_park_type_df["Lot >2h"] = split_demand(wkend_df["hrs_parked"], wkend_df["Lot >2h"], 4, 6)

    # Calculate Revenue and adjust for attrition

    wkdy_revenue_df = wkdy_park_type_df.copy()
    wkend_revenue_df = wkend_park_type_df.copy()


    # Adjust Demand Based on Attrition
    # ==================================
    wkdy_daily_effective_hrly_rate = wkdy_daily_rate / (wkdy_end_time - wkdy_start_time)
    wkend_daily_effective_hrly_rate = wkend_daily_rate / (wkend_end_time - wkend_start_time)

    daily_sensitivity = 5



    wkdy_revenue_df.loc["Hrly"] *= max(0,1-attrition_rate*wkdy_hrly_rate) * wkdy_hrly_rate
    wkdy_revenue_df.loc["Daily"] *= max(0,1-attrition_rate*wkdy_daily_effective_hrly_rate*daily_sensitivity) * wkdy_daily_rate

    # Adjust Weekend Demand Based on Attrition
    # ==================================
    wkend_revenue_df.loc["Hrly"] *= max(0,1-attrition_rate*wkend_hrly_rate) * wkend_hrly_rate
    wkend_revenue_df.loc["Daily"] *= max(0,1-attrition_rate*wkend_daily_effective_hrly_rate*daily_sensitivity) * wkend_daily_rate

    # add up df
    # add up weekday revenue
    wkdy_revenue = wkdy_revenue_df.sum(axis=1)

    # add up weekend revenue
    wkend_revenue = wkend_revenue_df.sum(axis=1)


    # convert weekday_seg_revenue into a yearly_revenue using ULI factors

    # convert weekday_seg_revenue into a yearly_revenue using ULI factors

    # read in ULI factors
    ULI_df = pd.read_excel(r"data\ULI Factors.xlsx")
    monthly_df = ULI_df.copy()
    monthly_df["wkdy_revenue_hrly"] = wkdy_revenue.iloc[0]
    monthly_df["wkdy_revenue_daily"] = wkdy_revenue.iloc[1]
    monthly_df["wkend_revenue_hrly"] = wkend_revenue.iloc[0]
    monthly_df["wkend_revenue_daily"] = wkend_revenue.iloc[1]
    monthly_df["Monthly Weekday Revenue_hrly"] = monthly_df["wkdy_revenue_hrly"] * 5/7 * monthly_df["Days in the Month"] * monthly_df["Multiplying Factor"]
    monthly_df["Monthly Weekday Revenue_daily"] = monthly_df["wkdy_revenue_daily"] * 5/7 * monthly_df["Days in the Month"] * monthly_df["Multiplying Factor"]
    monthly_df["Monthly Weekend Revenue_hrly"] = monthly_df["wkend_revenue_hrly"] * (sunday_parking_bool+1)/7 * monthly_df["Days in the Month"] * monthly_df["Multiplying Factor"]
    monthly_df["Monthly Weekend Revenue_daily"] = monthly_df["wkend_revenue_daily"] * (sunday_parking_bool+1)/7 * monthly_df["Days in the Month"] * monthly_df["Multiplying Factor"]

    monthly_df["Total Monthly Revenue_hrly"] = monthly_df["Monthly Weekday Revenue_hrly"] + monthly_df["Monthly Weekend Revenue_hrly"]
    monthly_df["Total Monthly Revenue_daily"] = monthly_df["Monthly Weekday Revenue_daily"] + monthly_df["Monthly Weekend Revenue_daily"]

    year_one_revenue_hrly = monthly_df["Total Monthly Revenue_hrly"].sum()
    year_one_revenue_daily = monthly_df["Total Monthly Revenue_daily"].sum()

    # calculate permit revenue
    year_one_revenue_permit = permit_count_adjusted * permit_rate * 12

    # convert year revenue into multiple years
    beginning_year = 2027
    years = np.arange(beginning_year,beginning_year+time_range,1) 
    yearly_revenue_expenses = pd.DataFrame()
    yearly_revenue_expenses["Years"] = years

    # increase revenue annually, then convert to today's dollars
    year_index = np.arange(time_range)

    yearly_revenue_expenses["Hrly Revenue"] = year_one_revenue_hrly
    yearly_revenue_expenses["Daily Revenue"] = year_one_revenue_daily
    yearly_revenue_expenses["Permit Revenue"] = year_one_revenue_permit
    if RPP_mode == "Existing":
        year_one_revenue_RPP = rpp_price * 878 # 878 is the current amount of RPP users
    elif RPP_mode == "Expanded":
        year_one_revenue_RPP = rpp_price * 878/956 * 1489 # use same % of active RPP households * total households
    yearly_revenue_expenses["RPP Revenue"] = year_one_revenue_RPP
    yearly_revenue_expenses["Total Revenue"] = year_one_revenue_hrly + year_one_revenue_daily + year_one_revenue_permit + year_one_revenue_RPP


    # expenses
    expenses_df = pd.read_excel(r"data\Expenses.xlsx")
    expense_scenario = expenses_df[(expenses_df["RPP Scenario"] ==RPP_mode)&(expenses_df["Parking Provider"] ==parking_operator)&(expenses_df["Parking Meter Type"] ==meter_type)]

    yoy_increase = expense_scenario["YOY Increase"].iloc[0] + 1
    enforcement_cost = expense_scenario["Enforcement Cost"].iloc[0]
    if (sunday_parking_bool == True)&(RPP_mode == "Existing"):
        enforcement_cost = enforcement_cost * 152/144
    elif (sunday_parking_bool == True)&(RPP_mode == "Expanded"):
        enforcement_cost = enforcement_cost * 200/192

    parking_mgmt_cost = expense_scenario["Parking Management Cost"].iloc[0]

    yearly_revenue_expenses["Enforcement Costs"] = (enforcement_cost* (yoy_increase ** year_index))
    yearly_revenue_expenses["Parking Mngmt Costs"] = (parking_mgmt_cost * (yoy_increase ** year_index))
    if time_range == 3:
        yearly_revenue_expenses["CapEX"] = expense_scenario[r"Cap Ex Amoritized, 10% over 3 yrs"].iloc[0]
    elif time_range == 5:
        yearly_revenue_expenses["CapEX"] = expense_scenario[r"Cap Ex Amoritized, 10% over 5 yrs"].iloc[0]
    yearly_revenue_expenses["Total Expenses"] = yearly_revenue_expenses["Enforcement Costs"] + yearly_revenue_expenses["Parking Mngmt Costs"] + yearly_revenue_expenses["CapEX"]
    yearly_revenue_expenses["Net Income"] = yearly_revenue_expenses["Total Revenue"] - yearly_revenue_expenses["Total Expenses"] 

    return(yearly_revenue_expenses)


