"""Helpers to read the processed star schema."""
import pandas as pd

from . import config as C


def load_fact_sales() -> pd.DataFrame:
    files = sorted((C.PROCESSED_DIR / "fact_sales").glob("fact_sales_*.csv"))
    df = pd.concat((pd.read_csv(f, parse_dates=["invoice_datetime"],
                                dtype={"stock_code": str, "invoice_no": str})
                    for f in files), ignore_index=True)
    df["cohort_index"] = df["cohort_index"].astype("Int64")
    return df


def load_table(name: str, **kwargs) -> pd.DataFrame:
    return pd.read_csv(C.PROCESSED_DIR / f"{name}.csv", **kwargs)


def load_all():
    """Return a dict with every table of the star schema."""
    return {
        "sales": load_fact_sales(),
        "returns": load_table("fact_returns", parse_dates=["invoice_datetime"],
                              dtype={"stock_code": str, "invoice_no": str}),
        "customers": load_table("dim_customer", parse_dates=["first_purchase_date", "last_purchase_date", "cohort_month"]),
        "products": load_table("dim_product", dtype={"stock_code": str}),
        "dates": load_table("dim_date", parse_dates=["date"]),
        "countries": load_table("dim_country"),
    }


def update_metrics(new: dict):
    """Merge headline numbers into outputs/key_metrics.json (used by the README)."""
    import json
    C.OUTPUTS_DIR.mkdir(exist_ok=True)
    path = C.OUTPUTS_DIR / "key_metrics.json"
    data = json.loads(path.read_text()) if path.exists() else {}
    data.update(new)
    path.write_text(json.dumps(data, indent=2, default=float))
    return data
