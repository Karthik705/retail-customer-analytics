# DAX Measures

Create an empty table called **`_Measures`** (Home → Enter data → load an empty table) and store every measure there, grouped into **display folders** (Model view → select measure → Properties → Display folder). A clean field list is something interviewers notice.

**Prerequisites** (set up in `dashboard_build_guide.md`, steps 2–4):
- `dim_date` is marked as the date table (on the `date` column).
- `customer_insights` is merged into `dim_customer` in Power Query, so segment, risk and campaign columns live on `dim_customer`.
- `fact_sales` and `fact_returns` each have an `invoice_date` column (Date type), added in Power Query.

---

## 1. Core KPIs · folder `1 Core`

```DAX
Gross Sales = SUM ( fact_sales[line_value] )

Returns Value = SUM ( fact_returns[line_value] )

Net Revenue = [Gross Sales] - [Returns Value]

Orders = DISTINCTCOUNT ( fact_sales[invoice_no] )

Units Sold = SUM ( fact_sales[quantity] )

Avg Order Value = DIVIDE ( [Gross Sales], [Orders] )

Return Rate % = DIVIDE ( [Returns Value], [Gross Sales] )

-- Guest checkouts (customer_id 0) are excluded from every customer count
Active Customers =
CALCULATE (
    DISTINCTCOUNT ( fact_sales[customer_id] ),
    dim_customer[is_guest] = FALSE ()
)

Revenue per Customer =
DIVIDE (
    CALCULATE ( [Net Revenue], dim_customer[is_guest] = FALSE () ),
    [Active Customers]
)

Guest Revenue Share % =
DIVIDE ( CALCULATE ( [Gross Sales], dim_customer[is_guest] = TRUE () ), [Gross Sales] )
```

## 2. Time intelligence · folder `2 Time`

```DAX
Last Data Date =
CALCULATE ( MAX ( fact_sales[invoice_date] ), REMOVEFILTERS () )

Net Revenue PY =
CALCULATE ( [Net Revenue], SAMEPERIODLASTYEAR ( dim_date[date] ) )

-- Like-for-like prior year. The data ends on 9 Dec 2011, so plain
-- SAMEPERIODLASTYEAR would compare 9 days of Dec-2011 with 31 days of Dec-2010
-- (a fake -42% "drop"). This version caps last year at the same calendar day.
Net Revenue PY (LFL) =
VAR LastDate = [Last Data Date]
VAR PYDates =
    FILTER (
        SAMEPERIODLASTYEAR ( dim_date[date] ),
        dim_date[date] <= EDATE ( LastDate, -12 )
    )
RETURN
    CALCULATE ( [Net Revenue], PYDates )

Net Revenue YoY % =
DIVIDE ( [Net Revenue] - [Net Revenue PY (LFL)], [Net Revenue PY (LFL)] )

Net Revenue YTD = TOTALYTD ( [Net Revenue], dim_date[date] )

Net Revenue Running Total =
CALCULATE (
    [Net Revenue],
    FILTER ( ALL ( dim_date[date] ), dim_date[date] <= MAX ( dim_date[date] ) )
)

Net Revenue 3M Moving Avg =
CALCULATE (
    AVERAGEX ( VALUES ( dim_date[year_month] ), [Net Revenue] ),
    DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -3, MONTH )
)

Net Revenue MoM % =
VAR PrevMonth =
    CALCULATE ( [Net Revenue], DATEADD ( dim_date[date], -1, MONTH ) )
RETURN
    DIVIDE ( [Net Revenue] - PrevMonth, PrevMonth )

-- KPI-card subtitle, e.g. "▲ 2.3% vs LY"
YoY Label =
VAR g = [Net Revenue YoY %]
RETURN
    IF ( ISBLANK ( g ), "No prior year",
        IF ( g >= 0, "▲ ", "▼ " ) & FORMAT ( ABS ( g ), "0.0%" ) & " vs LY" )

-- Used for conditional formatting (Format → Callout/Label → fx → Field value)
YoY Colour = IF ( [Net Revenue YoY %] >= 0, "#2A9D8F", "#E76F51" )
```

## 3. Products & Pareto · folder `3 Product`

```DAX
Product Revenue Rank =
RANKX ( ALLSELECTED ( dim_product[description] ), [Gross Sales], , DESC, DENSE )

-- Cumulative revenue share for the Pareto combo chart
Pareto Cumulative % =
VAR CurrentSales = [Gross Sales]
VAR AllProducts =
    ADDCOLUMNS ( ALLSELECTED ( dim_product[description] ), "@sales", [Gross Sales] )
VAR Cumulative =
    SUMX ( FILTER ( AllProducts, [@sales] >= CurrentSales ), [@sales] )
RETURN
    DIVIDE ( Cumulative, SUMX ( AllProducts, [@sales] ) )

-- ABC classification: A = products making up the first 80% of revenue
Pareto Class =
VAR c = [Pareto Cumulative %]
RETURN
    SWITCH ( TRUE (), ISBLANK ( c ), BLANK (), c <= 0.80, "A", c <= 0.95, "B", "C" )

Products for 80% Revenue =
VAR T =
    ADDCOLUMNS ( ALLSELECTED ( dim_product[description] ), "@cum", [Pareto Cumulative %] )
RETURN
    COUNTROWS ( FILTER ( T, [@cum] <= 0.80 ) )

Share of Products for 80% Revenue =
DIVIDE (
    [Products for 80% Revenue],
    COUNTROWS ( FILTER ( ALLSELECTED ( dim_product[description] ), [Gross Sales] > 0 ) )
)

High Return Flag = IF ( [Return Rate %] > 0.05, "High returns", "Normal" )
```

## 4. Customers, cohorts & funnel · folder `4 Customer`

```DAX
-- Cohort matrix: rows = dim_customer[cohort_month], columns = fact_sales[cohort_index]
Cohort Size =
CALCULATE ( [Active Customers], fact_sales[cohort_index] = 0 )

Retention % = DIVIDE ( [Active Customers], [Cohort Size] )

Repeat Customer Rate % =
VAR Cust =
    CALCULATETABLE ( VALUES ( fact_sales[customer_id] ), dim_customer[is_guest] = FALSE () )
RETURN
    DIVIDE (
        COUNTROWS ( FILTER ( Cust, CALCULATE ( DISTINCTCOUNT ( fact_sales[invoice_no] ) ) >= 2 ) ),
        COUNTROWS ( Cust )
    )

Avg Orders per Customer =
DIVIDE ( CALCULATE ( [Orders], dim_customer[is_guest] = FALSE () ), [Active Customers] )

-- Funnel: needs the disconnected table 'Funnel Stages' (build guide, step 5)
Customers Reaching Stage =
VAR MinOrders = SELECTEDVALUE ( 'Funnel Stages'[MinOrders] )
VAR Cust =
    CALCULATETABLE ( VALUES ( fact_sales[customer_id] ), dim_customer[is_guest] = FALSE () )
RETURN
    COUNTROWS ( FILTER ( Cust, CALCULATE ( DISTINCTCOUNT ( fact_sales[invoice_no] ) ) >= MinOrders ) )

Segment Customers =
CALCULATE ( COUNTROWS ( dim_customer ), NOT ISBLANK ( dim_customer[segment] ) )

Segment Revenue Share % =
DIVIDE (
    SUM ( dim_customer[monetary] ),
    CALCULATE ( SUM ( dim_customer[monetary] ), REMOVEFILTERS ( dim_customer[segment] ) )
)

Top 20% Customer Revenue Share % =
VAR Cust =
    ADDCOLUMNS (
        CALCULATETABLE ( VALUES ( dim_customer[customer_id] ), dim_customer[is_guest] = FALSE () ),
        "@rev", CALCULATE ( [Net Revenue] )
    )
VAR Positive = FILTER ( Cust, [@rev] > 0 )
VAR TopN = ROUNDUP ( COUNTROWS ( Positive ) * 0.2, 0 )
RETURN
    DIVIDE ( SUMX ( TOPN ( TopN, Positive, [@rev], DESC ), [@rev] ), SUMX ( Positive, [@rev] ) )
```

## 5. Churn & retention campaign · folder `5 Churn`

First create two **What-if parameters** (Modeling → New parameter → Numeric range):
- `Save Rate`: 0.05 → 0.30, increment 0.01, default 0.15
- `Cost per Customer`: 0 → 50, increment 1, default 10

Power BI auto-creates the measures `[Save Rate Value]` and `[Cost per Customer Value]` plus a slider for each.

```DAX
Scored Customers =
CALCULATE ( COUNTROWS ( dim_customer ), NOT ISBLANK ( dim_customer[churn_probability] ) )

Avg Churn Probability = AVERAGE ( dim_customer[churn_probability] )

High-Risk Customers =
CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[risk_tier] = "High" )

Revenue at Risk (90d) = SUM ( dim_customer[revenue_at_risk_90d] )

Tier 1 Customers =
CALCULATE ( COUNTROWS ( dim_customer ), dim_customer[campaign_tier] = "Tier 1 - personal outreach" )

-- Scenario measures driven by the What-if sliders
Campaign Recovery (scenario) =
CALCULATE (
    SUMX ( dim_customer, dim_customer[churn_probability] * dim_customer[expected_quarterly_spend] ),
    dim_customer[campaign_tier] = "Tier 1 - personal outreach"
) * [Save Rate Value]

Campaign Cost (scenario) = [Tier 1 Customers] * [Cost per Customer Value]

Campaign Net Benefit = [Campaign Recovery (scenario)] - [Campaign Cost (scenario)]

Campaign ROI = DIVIDE ( [Campaign Net Benefit], [Campaign Cost (scenario)] )

Campaign ROI Label = FORMAT ( [Campaign ROI], "0.0" ) & "x ROI"
```

With the defaults (15% save rate, £10 per customer), `Campaign Recovery (scenario)` should show ≈ **£42.4K**, `Campaign Cost` **£8,520**, and ROI ≈ **4.0x**. These match notebook 04, which is a good check that your model is wired correctly.

## 6. Geography · folder `6 Geo`

```DAX
International Revenue Share % =
DIVIDE ( CALCULATE ( [Gross Sales], dim_country[is_domestic] = FALSE () ), [Gross Sales] )

Countries Served =
CALCULATE ( DISTINCTCOUNT ( fact_sales[country] ), fact_sales[country] <> "Unspecified" )

Market Rank =
RANKX ( ALLSELECTED ( dim_country[country] ), [Gross Sales], , DESC, DENSE )
```

## 7. Dynamic titles & helpers · folder `7 UI`

```DAX
Selected Period Label =
VAR MinD = MIN ( dim_date[date] )
VAR MaxD = MIN ( MAX ( dim_date[date] ), [Last Data Date] )
RETURN
    FORMAT ( MinD, "d mmm yyyy" ) & " – " & FORMAT ( MaxD, "d mmm yyyy" )

Overview Title =
"Net revenue " & FORMAT ( [Net Revenue], "£#,0" ) & "  |  " & [Selected Period Label]

Drillthrough Customer Title =
"Customer " & SELECTEDVALUE ( dim_customer[customer_id], "(select one)" )
    & " · " & SELECTEDVALUE ( dim_customer[segment], "" )

Partial Month Note =
IF ( MAX ( dim_date[date] ) >= DATE ( 2011, 12, 1 ), "Note: Dec-2011 contains data to the 9th only", "" )
```

## Format strings
Set these in the Measure tools ribbon so every visual shows consistent units:
- Currency: `£#,0` (on charts with big numbers use `£#,0,K` to show thousands)
- Percentages: `0.0%`
- Counts: `#,0`

## Validation checklist (compare with the Python/SQL numbers)
| Measure (no filters) | Expected |
|---|---|
| Gross Sales | £19,643,862 |
| Returns Value | £716,426 |
| Net Revenue | £18,927,436 |
| Orders | 39,516 |
| Active Customers | 5,852 |
| Return Rate % | 3.65% |
| Share of Products for 80% Revenue | ≈ 21% |
| Revenue at Risk (90d) | ≈ £578K |
