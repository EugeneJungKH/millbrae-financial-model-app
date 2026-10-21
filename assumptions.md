# Parking Demand and Revenue

1. **Parking Data Collection:** Revenue estimates are based on parking-duration data collected on:
   - **Weekday:** May 4, 2023 (Thursday)
   - **Weekend:** May 6, 2023 (Saturday)

2. **Hours of Data Collection:** Parking data was collected from 10:00 AM to 8:00 PM. When the modeled paid-parking hours differ from the data collection period, ULI time-of-day factors are used to adjust observed demand.

3. **Annual Demand Extrapolation:** ULI monthly factors are used to extrapolate observed weekday and weekend parking activity throughout the year.

4. **Representative Weekday:** Thursday parking activity is assumed to represent typical weekday parking demand. The model assumes five weekdays per week.

5. **Representative Weekend Day:** Saturday parking activity is assumed to represent weekend parking demand. If Sunday parking is enabled, Saturday parking demand is also used to represent Sunday demand.

6. **Parking Duration:** For each parking duration category in the raw data (0-1 hr, 1-2hr, etc), parker are assumed to park for the midpoint of each category (0.5 hr, 1.5 hr, etc)

7. **Hourly vs. Daily vs. Permit Parking:** Parking demand is divided into hourly, daily, and permit parking based on duration:
   - All-day parking and parking lots: sessions up to 4 hours are treated as hourly parking; sessions longer than 4 hours and up to 6 hours are treated as daily parking.
   - Two-hour parking: sessions up to 2 hours are treated as hourly parking; sessions longer than 2 hours and up to 6 hours are treated as daily parking.

8. **Permit-Eligible Parking:** Permit parkers were based on the number parking sessions longer than 6 hours on Thursday. It was then adjusted assuming that 80% of workers present during the obsserved Thursday parking period.

9. **Price-Based Attrition:** Parking demand is assumed to decrease linearly as parking rates increase. The attrition rate entered by the user is applied to hourly and daily parking demand. 

# Residential Parking Permit (RPP) Revenue

10. **Expanded RPP Program:** The Expanded RPP scenario assumes the existing participation rate (878 users out of 956 households) remains constant when applied to 1,489 households.

# Financial Analysis

11. **Model Start Year:** Financial results begin in 2027.

12. **Revenue Growth:** Hourly, daily, permit, and RPP revenues are held constant across the modeled years. There is no interest or fluctuation in demand considered.

13. **Expense Scenarios:** Enforcement costs, parking management costs, and capital costs are based on the selected combination of RPP scenario, parking operator, and parking meter type in the Expenses dataset.

14. **Sunday Enforcement Costs:** If Sunday paid parking is enabled, enforcement costs are increased using the adjustment specified in the model:
   - Existing RPP scenario: 152 / 144
   - Expanded RPP scenario: 200 / 192