"""Customer-level features as of a cutoff date (no data after the cutoff is used)."""
import numpy as np
import pandas as pd

from . import config as C

RFM_SEGMENT_MAP = {
    r"[1-2][1-2]": "Hibernating",
    r"[1-2][3-4]": "At Risk",
    r"[1-2]5": "Can't Lose Them",
    r"3[1-2]": "About to Sleep",
    r"33": "Need Attention",
    r"[3-4][4-5]": "Loyal Customers",
    r"41": "Promising",
    r"51": "New Customers",
    r"[4-5][2-3]": "Potential Loyalists",
    r"5[4-5]": "Champions",
}

SEGMENT_ACTIONS = {
    "Champions": "Reward & referral programme; early access to new ranges",
    "Loyal Customers": "Upsell higher-margin lines; loyalty tier benefits",
    "Potential Loyalists": "Membership offer; personalised recommendations",
    "New Customers": "Onboarding sequence; second-order incentive",
    "Promising": "Brand-awareness content; free-shipping threshold nudge",
    "Need Attention": "Limited-time offer based on past categories",
    "About to Sleep": "Reactivation email with best-sellers in their categories",
    "At Risk": "Personal outreach + win-back discount before they lapse",
    "Can't Lose Them": "Account-manager call; tailored offer — highest priority",
    "Hibernating": "Low-cost seasonal campaign only (e.g. pre-Christmas)",
}


def _known(sales):
    return sales[sales["customer_id"] != C.GUEST_CUSTOMER_ID]


def rfm_table(sales: pd.DataFrame, returns: pd.DataFrame, as_of) -> pd.DataFrame:
    as_of = pd.Timestamp(as_of)
    s = _known(sales[sales["invoice_datetime"] < as_of])
    r = _known(returns[returns["invoice_datetime"] < as_of])
    g = s.groupby("customer_id")
    rfm = pd.DataFrame({
        "recency_days": (as_of - g["invoice_datetime"].max()).dt.days,
        "frequency": g["invoice_no"].nunique(),
        "gross_sales": g["line_value"].sum(),
    })
    rfm["returns_value"] = r.groupby("customer_id")["line_value"].sum().reindex(rfm.index).fillna(0)
    rfm["monetary"] = (rfm["gross_sales"] - rfm["returns_value"]).clip(lower=0)
    return rfm


def score_rfm(rfm: pd.DataFrame) -> pd.DataFrame:
    out = rfm.copy()
    # rank(method="first") breaks ties so qcut always produces 5 equal bins
    out["R"] = pd.qcut(out["recency_days"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    out["F"] = pd.qcut(out["frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["M"] = pd.qcut(out["monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    out["RFM_score"] = out["R"].astype(str) + out["F"].astype(str) + out["M"].astype(str)
    rf = out["R"].astype(str) + out["F"].astype(str)
    out["segment"] = rf.replace(RFM_SEGMENT_MAP, regex=True)
    out["recommended_action"] = out["segment"].map(SEGMENT_ACTIONS)
    return out


def churn_features(sales: pd.DataFrame, returns: pd.DataFrame, products: pd.DataFrame, cutoff) -> pd.DataFrame:
    """Behavioural features for customers active in the 365 days before `cutoff`."""
    cutoff = pd.Timestamp(cutoff)
    s = _known(sales[sales["invoice_datetime"] < cutoff])
    r = _known(returns[returns["invoice_datetime"] < cutoff])

    active = s.loc[s["invoice_datetime"] >= cutoff - pd.Timedelta(days=C.ACTIVE_LOOKBACK_DAYS), "customer_id"].unique()
    s = s[s["customer_id"].isin(active)]
    r = r[r["customer_id"].isin(active)]

    orders = (s.groupby(["customer_id", "invoice_no"])
              .agg(dt=("invoice_datetime", "min"), value=("line_value", "sum"),
                   items=("quantity", "sum"), lines=("stock_code", "size"))
              .reset_index().sort_values(["customer_id", "dt"]))
    orders["gap_days"] = orders.groupby("customer_id")["dt"].diff().dt.total_seconds() / 86400

    g = orders.groupby("customer_id")
    f = pd.DataFrame({
        "recency_days": (cutoff - g["dt"].max()).dt.days,
        "tenure_days": (cutoff - g["dt"].min()).dt.days,
        "frequency": g.size(),
        "monetary": g["value"].sum(),
        "avg_order_value": g["value"].mean(),
        "avg_items_per_order": g["items"].mean(),
        "avg_lines_per_order": g["lines"].mean(),
        "avg_gap_days": g["gap_days"].mean(),
        "std_gap_days": g["gap_days"].std(),
    })
    for days in (30, 90, 180):
        recent = orders[orders["dt"] >= cutoff - pd.Timedelta(days=days)]
        f[f"orders_last_{days}d"] = recent.groupby("customer_id").size().reindex(f.index).fillna(0)
        f[f"spend_last_{days}d"] = recent.groupby("customer_id")["value"].sum().reindex(f.index).fillna(0)

    last_year = orders[orders["dt"] >= cutoff - pd.Timedelta(days=365)]
    f["orders_last_365d"] = last_year.groupby("customer_id").size().reindex(f.index).fillna(0)
    # NET of returns: otherwise an order that was immediately cancelled
    # (e.g. customer 12346's 74,215-unit order) looks like a top customer
    gross_365 = last_year.groupby("customer_id")["value"].sum().reindex(f.index).fillna(0)
    ret_365 = (r[r["invoice_datetime"] >= cutoff - pd.Timedelta(days=365)]
               .groupby("customer_id")["line_value"].sum().reindex(f.index).fillna(0))
    f["spend_last_365d"] = (gross_365 - ret_365).clip(lower=0)

    prev = orders[(orders["dt"] >= cutoff - pd.Timedelta(days=180)) & (orders["dt"] < cutoff - pd.Timedelta(days=90))]
    f["spend_prev_90d"] = prev.groupby("customer_id")["value"].sum().reindex(f.index).fillna(0)
    f["spend_trend"] = (f["spend_last_90d"] - f["spend_prev_90d"]) / (f["spend_last_90d"] + f["spend_prev_90d"] + 1)

    # recency relative to the customer's own buying rhythm
    f["recency_vs_gap"] = f["recency_days"] / f["avg_gap_days"].fillna(f["tenure_days"]).clip(lower=1)

    f["distinct_products"] = s.groupby("customer_id")["stock_code"].nunique()
    cats = s.merge(products[["stock_code", "category"]], on="stock_code", how="left")
    f["distinct_categories"] = cats.groupby("customer_id")["category"].nunique()
    seasonal = cats[cats["category"] == "Christmas & Seasonal"].groupby("customer_id")["line_value"].sum()
    f["seasonal_spend_share"] = (seasonal.reindex(f.index).fillna(0) / f["monetary"]).fillna(0)

    f["return_rate"] = (r.groupby("customer_id")["line_value"].sum().reindex(f.index).fillna(0) / f["monetary"]).clip(upper=1)
    home = s.groupby("customer_id")["country"].agg(lambda x: x.value_counts().index[0])
    f["is_uk"] = (home == "United Kingdom").astype(int)

    f["std_gap_days"] = f["std_gap_days"].fillna(0)
    f["avg_gap_days"] = f["avg_gap_days"].fillna(-1)  # -1 = single-order customer
    # seasonality: churn is far lower just before the Q4 gifting season
    f["days_to_dec1"] = (pd.Timestamp(f"{cutoff.year}-12-01") - cutoff).days % 365
    f["snapshot"] = cutoff
    return f


def churn_labels(sales: pd.DataFrame, customers: pd.Index, cutoff) -> pd.Series:
    """1 = no purchase in the CHURN_WINDOW_DAYS after the cutoff."""
    cutoff = pd.Timestamp(cutoff)
    window = sales[(sales["invoice_datetime"] >= cutoff) &
                   (sales["invoice_datetime"] < cutoff + pd.Timedelta(days=C.CHURN_WINDOW_DAYS))]
    bought = set(window["customer_id"])
    return pd.Series([0 if c in bought else 1 for c in customers], index=customers, name="churned")


def future_spend(sales: pd.DataFrame, customers: pd.Index, cutoff) -> pd.Series:
    cutoff = pd.Timestamp(cutoff)
    window = sales[(sales["invoice_datetime"] >= cutoff) &
                   (sales["invoice_datetime"] < cutoff + pd.Timedelta(days=C.CHURN_WINDOW_DAYS))]
    return window.groupby("customer_id")["line_value"].sum().reindex(customers).fillna(0)
