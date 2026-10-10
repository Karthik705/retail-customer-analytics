# Business Recommendations

*Audience: Head of E-commerce / CRM team. All figures in GBP; data window 1 Dec 2009 – 9 Dec 2011.*

## Executive summary

The business generated **£18.9M net revenue** from 5,852 identified customers, but growth has stalled (**+2.3% YoY**, Jan–Nov 2011 vs 2010) and revenue depends on a small group: **the top 20% of customers produce 77% of net revenue**. A churn model scores every active customer; **£578K of revenue is at risk in the next 90 days**, and a targeted two-tier retention campaign is expected to recover **~£42K from 852 customers at a cost of ~£8.5K (≈4.0x ROI)** in the first quarter alone.

## Findings and recommendations

### 1. Protect the top customers first
- Champions + Loyal Customers are **34% of customers but 80% of revenue**.
- 72 "Can't Lose Them" customers (formerly frequent, now gone quiet) hold **£479K** of lifetime revenue.
- **Recommendation:** assign account-manager outreach to "Can't Lose Them" and to high-value Tier 1 targets; add a loyalty tier for Champions (early access, volume pricing).

### 2. Fix the first-to-second order leak
- **27.6% of customers never place a second order**, and single-order customers churn at **72%** versus **19%** for customers with 8+ orders.
- **Recommendation:** a structured post-first-order journey (thank-you, best-sellers in the categories they bought, time-limited second-order incentive at day 30).

### 3. Act on "overdue" signals, not just inactivity
- Repeat customers who are **more than 2× past their usual reorder gap churn at 55%**, versus **35%** for those still on rhythm.
- A fixed "no order in 90 days" rule (AUC 0.66) misses this; the model (AUC 0.77) uses each customer's own rhythm.
- **Recommendation:** trigger win-back contact when a customer passes 1.5× their personal average gap, rather than on a single company-wide inactivity date.

### 4. Run a two-tier retention campaign

| Tier | Who | Action | Customers | Expected 90-day recovery |
|---|---|---|---|---|
| Tier 1 | Top 20% by expected recovery | Personal outreach + tailored offer | 852 | ~£42.4K |
| Tier 2 | Next 30% | Automated win-back email | 1,278 | ~£26.3K |
| — | Bottom 50% | No paid campaign (cost > expected return) | 3,722 | — |

Assumptions: 15% of contacted would-be churners are retained (sensitivity for Tier 1: 5% → £14.1K, 20% → £56.5K), £10 cost per contacted customer, and only the next 90 days of revenue are counted. Revenue retained beyond one quarter is upside.

**Measure it properly:** hold out a random 10% of Tier 1 as a control group so the true save rate can be measured, then feed it back into the model's ROI assumptions.

### 5. Plan for seasonality
- Sep–Dec delivers **44.5%** of annual revenue, and churn risk is seasonal (42% of active customers lapse in the 90 days after a September snapshot vs 69% after December).
- **Recommendation:** launch retention outreach in **late summer**, before the gifting season, when customers are most likely to return; avoid judging campaign performance in Jan–Mar against Q4.

### 6. Grow international accounts
- International orders are worth **£853 on average vs £464 for the UK** (1.8×), yet international markets are only 14.5% of sales.
- **Recommendation:** dedicated wholesale terms for the top European markets (Ireland, Netherlands, Germany, France).

### 7. Data quality fixes for the source system
- The two yearly Excel exports overlap by 9 days, which double-counts **£377K** if not handled.
- **22.8%** of transaction lines have no customer ID (13.1% of revenue): guest checkout prevents any retention marketing for these buyers.
- **Recommendation:** de-duplicate exports at source and incentivise account creation at checkout.

## Limitations
- No cost/margin data, so recovery is measured in revenue, not profit.
- Product categories are derived from description keywords (≈6% of revenue remains "Other").
- Customers active before Dec 2009 appear as "new" in the first cohort (left-censoring).
- The save rate is an assumption until measured with a control group.
