# Why each chart? Visualization design decisions

Why each visual was chosen. Each choice below follows one rule: **pick the chart that makes the comparison the viewer needs to make the easiest one to see.**

## Executive Overview

| Visual | Why this chart | Alternatives rejected |
|---|---|---|
| **KPI cards with YoY subtitle** | Executives scan, not read. One number plus direction (▲/▼) answers "are we OK?" in two seconds. | A table of KPIs: forces reading row by row. |
| **Column + line combo (monthly net revenue, 3-month moving average, prior year)** | Columns show discrete monthly amounts; the moving-average line removes noise so the Q4 seasonal pattern is obvious; the prior-year line gives a like-for-like benchmark on the same axis. | Two separate charts: the eye can't compare across them. A pie chart: can't show time. |
| **Area chart (running total)** | The filled area emphasises *accumulation*, which is what a running total represents. | Line chart: works, but reads as a rate rather than a stock. |

**Design detail:** the like-for-like prior-year measure exists because Dec-2011 has only 9 days of data. Without it, the chart would show a fake 42% "collapse" in December.

## Sales & Products

| Visual | Why this chart | Alternatives rejected |
|---|---|---|
| **Horizontal bar (category sales)** | Category names are long, and horizontal bars keep labels readable. Sorted bars make ranking instant. | Pie chart: 11 slices with similar sizes are impossible to compare accurately (angles are harder to judge than lengths). |
| **Treemap (category → product)** | Shows part-to-whole for *two levels at once* (hierarchy) in a compact space, and supports drill-down. | Sunburst: harder to read; nested bar: needs a lot of space. |
| **Pareto combo (bars + cumulative % line)** | The bars rank products; the line shows when 80% of revenue is reached. One chart proves the 80/20 claim (≈21% of products → 80% of revenue). | Plain bar chart: shows ranking but not concentration. |
| **Bar with conditional colour (return rate)** | Colour is used *only* to flag exceptions (> 5%), so the eye goes straight to problem categories. | Colouring every bar differently: decoration with no meaning. |
| **Matrix heatmap (weekday × hour)** | Two categorical dimensions and one value is exactly what a heatmap is for; patterns pop out: weekday 10:00–13:00 is the peak, Thursday is the strongest day, and there is almost no Saturday trading. | Line per weekday: 6 overlapping lines become spaghetti. |

## Customers (RFM & Cohorts)

| Visual | Why this chart | Alternatives rejected |
|---|---|---|
| **Cohort retention heatmap** | Rows = when customers joined, columns = months since joining. Colour intensity shows decay. Comparing diagonals and columns reveals whether newer cohorts behave worse. | Line chart per cohort: 25 lines are unreadable. |
| **RFM scatter (recency × frequency, bubble = spend, colour = segment)** | Shows the *distribution* of individual customers, not just averages, and makes the segment boundaries visible. Log scale on frequency because it is heavily right-skewed. | Bar chart of segment averages: hides the spread within each segment. |
| **Funnel (1st → 2nd → 3rd → 5th → 10th order)** | A funnel conveys sequential drop-off; the biggest leak (1st → 2nd order, 28% never return) is the first thing you see. | Bar chart: works, but loses the "stages" metaphor. |
| **Paired bars (% customers vs % revenue by segment)** | Putting the two shares side by side shows imbalance directly: Champions are 14% of customers but 52% of revenue. | Two pie charts: comparing across pies is unreliable. |

## Churn & Retention Campaign

| Visual | Why this chart | Alternatives rejected |
|---|---|---|
| **What-if sliders + scenario cards** | Turns a static estimate into a decision tool: managers can test their own save-rate assumption and see ROI change. It also makes the model's assumptions explicit. | A fixed number in a text box: hides assumptions. |
| **Segment × risk matrix** | Cross-tab of two categorical variables is a natural matrix; it shows the two models (RFM and churn) agree and where they disagree. | Stacked bars: harder to read exact counts. |
| **Stacked bar (revenue at risk by segment and tier)** | Answers "where is the money at risk?", which is a business question, not a model-accuracy question. | Pie: can't show the second dimension (risk tier). |
| **Sorted table with data bars (call list)** | The output of the analysis is a list of *who to call*. A table is the right tool when people need exact values and IDs; data bars add a quick visual rank. | Any chart: you can't phone a bubble. |
| **SHAP summary image** | Explains *why* the model flags customers, building trust in the scores. | Feature-importance bar chart: shows magnitude but not direction (does more orders mean more or less churn?). |

## Geography

| Visual | Why this chart | Alternatives rejected |
|---|---|---|
| **Bubble map** | Geography is the natural frame for "where", and bubble size encodes revenue without distorting by country area (a filled map makes big countries look important). | Filled map only: Australia would visually dominate despite modest revenue. |
| **Top-10 international bar** | The map gives the overview; the bar gives exact ranking. UK (85% of sales) is excluded so international markets are actually visible. | Including the UK: one bar would flatten all others. |

## General principles applied throughout
1. **One question per page**, stated in the page title.
2. **Colour has meaning:** navy = primary metric, teal = good/positive, coral = bad/alert, grey = context. The same palette is used in the Python charts and the Power BI theme.
3. **No 3D, no gauges, no pie charts with more than 3 slices.**
4. **Titles state the insight** ("Top 20% of customers = 77% of revenue"), not the field names.
5. **Detail on demand:** summary visuals on the page, specifics through drill-through and tooltips.
