"""Data loading, cleaning and star-schema construction for Online Retail II."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from . import config as C

# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------

def find_raw_file():
    for path in C.RAW_FILE_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Raw file not found. Run `python -m src.download_data` or place "
        "online_retail_II.xlsx in data/raw/."
    )


def load_raw(path=None) -> pd.DataFrame:
    """Read both yearly sheets and tag each row with its source sheet."""
    path = path or find_raw_file()
    engine = "pyxlsb" if str(path).endswith(".xlsb") else "openpyxl"
    frames = []
    for sheet in C.SHEETS:
        part = pd.read_excel(path, sheet_name=sheet, engine=engine)
        part["source_sheet"] = sheet
        frames.append(part)
    df = pd.concat(frames, ignore_index=True)

    # .xlsb stores dates as Excel serial numbers; .xlsx returns datetimes
    if not pd.api.types.is_datetime64_any_dtype(df["InvoiceDate"]):
        df["InvoiceDate"] = pd.to_datetime(
            df["InvoiceDate"], unit="D", origin="1899-12-30"
        )
    df["InvoiceDate"] = df["InvoiceDate"].dt.round("min")

    df = df.rename(columns={
        "Invoice": "invoice_no", "StockCode": "stock_code",
        "Description": "description", "Quantity": "quantity",
        "InvoiceDate": "invoice_datetime", "Price": "unit_price",
        "Customer ID": "customer_id", "Country": "country",
    })
    for col in ["invoice_no", "stock_code"]:
        df[col] = df[col].astype(str).str.strip()
    df["description"] = df["description"].astype("string").str.strip().str.upper()
    df["country"] = df["country"].astype(str).str.strip()
    return df


# ----------------------------------------------------------------------------
# Cleaning helpers
# ----------------------------------------------------------------------------

class QualityLog:
    """Records every cleaning step with rows and revenue affected."""

    def __init__(self, df: pd.DataFrame):
        self.rows = []
        self.add("Raw data loaded (both sheets)", 0, df)

    def add(self, step: str, removed: int, remaining_df: pd.DataFrame, note: str = ""):
        value = (remaining_df["quantity"] * remaining_df["unit_price"]).sum()
        self.rows.append({
            "step": step,
            "rows_affected": int(removed),
            "rows_remaining": int(len(remaining_df)),
            "line_value_remaining": round(float(value), 2),
            "note": note,
        })

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows)


def is_non_product(code: pd.Series) -> pd.Series:
    upper_set = {c.upper() for c in C.NON_PRODUCT_CODES}
    return code.str.upper().isin(upper_set) | code.str.startswith(C.NON_PRODUCT_PREFIXES)


# Ordered keyword rules: first match wins.
CATEGORY_RULES = [
    ("Christmas & Seasonal", r"CHRISTMAS|XMAS|ADVENT|SANTA|REINDEER|SNOWFLAKE|SNOWMAN|BAUBLE|NATIVITY|EASTER|HALLOWEEN|PAPER CHAIN"),
    ("Stationery & Crafts", r"PAPER CRAFT|CRAFT KIT"),
    ("Lighting & Candles", r"LIGHT|LANTERN|CANDLE|LAMP|CHANDELIER|T-LIGHT|TEALIGHT|\bLED\b"),
    ("Personal & Accessories", r"HOT WATER BOTTLE|HOTTIE|JEWEL|NECKLACE|BRACELET|EARRING|\bHAIR|\bRING\b|BROOCH|SCARF|GLOVE|SLIPPER|HAND WARMER|COLLAR|PLASTERS|COMPACT MIRROR|\bLIP|\bSOAP|TOWEL|\bBATH"),
    ("Kitchen & Dining", r"CAKE|\bMUGS?\b|\bCUPS?\b|PLATE|BOWL|\bTEA\b|TEAPOT|TEACUP|COFFEE|CUTLERY|BAKING|\bJAM\b|\bJARS?\b|KITCHEN|PANTRY|SPOON|NAPKIN|TRAY|BOTTLE OPENER|\bJUG|GLASS|SNACK|POPCORN|RECIPE|APRON|OVEN|TOAST|\bEGG|BISCUIT|DINER|PICNIC|LUNCH BOX|CHOPSTICK|TUMBLER|BEAKER|SCALES|\bTINS?\b|BREAD"),
    ("Bags & Storage", r"\bBAGS?\b|SHOPPER|STORAGE|BASKET|HAMPER|TOTE|PURSE|BOXES|DRAWER|CHEST|\bCASE|CUBES"),
    ("Party & Gift Wrap", r"PARTY|BUNTING|BALLOON|BIRTHDAY|RIBBON|CONFETTI|TISSUE|WRAP|GIFT|BANNER|\bCARDS?\b(?! HOLDER)|STICKER"),
    ("Home Decor", r"SIGN|FRAME|DOORMAT|CLOCK|CUSHION|HEART|WICKER|ORNAMENT|MIRROR|VASE|HOOK|CABINET|CHALKBOARD|MEMOBOARD|BOARD|WALL|DECORATION|GARLAND|DOOR|KNOB|PLAQUE|WREATH|BIRD|FLOWER|ROSE|BUTTERFLY|HANGING|COAT RACK|SHELF|PLANTER|\bPOT\b|TRINKET|PHOTO|FLAG"),
    ("Stationery & Crafts", r"\bPEN\b|PENCIL|NOTEBOOK|NOTE BOOK|SEWING|FELTCRAFT|CRAFT|TAPE|ERASER|RUBBER|PAPER|JOURNAL|DIARY|CALENDAR|STAMP|CRAYON|COLOURING|\bBOOK|ENVELOPE|\bCLIP|PAINT SET"),
    ("Toys & Kids", r"\bTOY|DOLL|CHILDRENS|CHILDS|KIDS|GAME|SPACEBOY|HARMONICA|PLAYHOUSE|JIGSAW|SKIPPING|BLOCK|PUPPET|TEDDY|DOMINO|SPINNING|MAGIC|BINGO|CIRCUS|RACING|SOLDIER|BABY"),
    ("Garden & Outdoor", r"GARDEN|PARASOL|UMBRELLA|WATERING|PLANT|SEED|BIRDHOUSE|BIRD HOUSE|GNOME|OUTDOOR|THERMOMETER"),
]
_COMPILED_RULES = [(name, re.compile(pattern)) for name, pattern in CATEGORY_RULES]


def categorize(description: str) -> str:
    if not isinstance(description, str):
        return "Other"
    for name, pattern in _COMPILED_RULES:
        if pattern.search(description):
            return name
    return "Other"


# ----------------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------------

def clean(df: pd.DataFrame):
    """Return (sales_lines, return_lines, fee_lines, quality_log)."""
    log = QualityLog(df)

    # 1. Sheet overlap: drop sheet-1 rows from the overlapping 9 days
    overlap = (df["source_sheet"] == C.SHEETS[0]) & (
        df["invoice_datetime"] >= pd.Timestamp(C.SHEET_OVERLAP_START)
    )
    df = df.loc[~overlap].copy()
    log.add("Removed overlap between the two Excel sheets (2010-12-01 to 2010-12-09)",
            overlap.sum(), df, "Same invoices appear in both yearly sheets")

    # 2. Exact duplicate lines
    key_cols = [c for c in df.columns if c != "source_sheet"]
    dup = df.duplicated(subset=key_cols)
    df = df.loc[~dup].copy()
    log.add("Removed exact duplicate rows", dup.sum(), df)

    # 3. Non-product lines (postage, fees, manual adjustments, vouchers, tests)
    non_prod = is_non_product(df["stock_code"])
    fee_lines = df.loc[non_prod].copy()
    df = df.loc[~non_prod].copy()
    log.add("Separated non-product lines (postage, fees, adjustments, vouchers)",
            non_prod.sum(), df, "Saved to fact_fees; excluded from product analysis")

    # 4. Cancellations become the returns table
    is_cancel = df["invoice_no"].str.startswith("C")
    return_lines = df.loc[is_cancel].copy()
    df = df.loc[~is_cancel].copy()
    log.add("Separated cancelled/returned lines (invoice starts with 'C')",
            is_cancel.sum(), df, "Saved to fact_returns")

    # 5. Invalid sales lines: non-positive quantity or price (stock write-offs,
    #    damages, 'A' bad-debt adjustments, free samples)
    invalid = (df["quantity"] <= 0) | (df["unit_price"] <= 0)
    df = df.loc[~invalid].copy()
    log.add("Removed lines with quantity <= 0 or price <= 0",
            invalid.sum(), df, "Stock adjustments / write-offs / zero-price samples")

    # 6. Return lines must also be valid
    return_lines = return_lines[(return_lines["unit_price"] > 0)].copy()
    return_lines["quantity"] = return_lines["quantity"].abs()

    # 7. Guest (missing Customer ID) -> surrogate key 0
    n_guest = df["customer_id"].isna().sum()
    for frame in (df, return_lines, fee_lines):
        frame["customer_id"] = frame["customer_id"].fillna(C.GUEST_CUSTOMER_ID).astype(int)
    log.add("Mapped missing Customer IDs to guest key 0 (kept for sales KPIs)",
            n_guest, df, "Excluded from customer-level analysis (RFM, churn, cohorts)")

    # 8. Country standardisation
    for frame in (df, return_lines, fee_lines):
        frame["country"] = frame["country"].replace(C.COUNTRY_FIXES)
    log.add("Standardised country names (EIRE->Ireland, RSA->South Africa, ...)", 0, df)

    for frame in (df, return_lines):
        frame["line_value"] = (frame["quantity"] * frame["unit_price"]).round(2)

    return df, return_lines, fee_lines, log.to_frame()


def canonical_descriptions(*frames: pd.DataFrame) -> pd.Series:
    """Most frequent non-null description per stock code."""
    allrows = pd.concat([f[["stock_code", "description"]] for f in frames])
    allrows = allrows.dropna(subset=["description"])
    allrows = allrows[allrows["description"].str.len() > 0]
    return (allrows.groupby("stock_code")["description"]
            .agg(lambda s: s.value_counts().index[0]))


def build_dim_product(sales: pd.DataFrame, returns: pd.DataFrame) -> pd.DataFrame:
    desc = canonical_descriptions(sales, returns)
    codes = pd.Index(sorted(set(sales["stock_code"]) | set(returns["stock_code"])), name="stock_code")
    dim = pd.DataFrame(index=codes).join(desc).reset_index()
    dim["description"] = dim["description"].fillna("UNKNOWN PRODUCT")
    dim["category"] = dim["description"].map(categorize)
    first_price = sales.groupby("stock_code")["unit_price"].median().rename("median_unit_price")
    return dim.merge(first_price, on="stock_code", how="left")


def build_dim_date(start, end) -> pd.DataFrame:
    dates = pd.date_range(pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize(), freq="D")
    dim = pd.DataFrame({"date": dates})
    dim["date_key"] = dim["date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"] = dim["date"].dt.year
    dim["quarter"] = "Q" + dim["date"].dt.quarter.astype(str)
    dim["month_num"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.strftime("%b")
    dim["year_month"] = dim["date"].dt.strftime("%Y-%m")
    dim["week_of_year"] = dim["date"].dt.isocalendar().week.astype(int)
    dim["day_of_week_num"] = dim["date"].dt.dayofweek + 1
    dim["day_name"] = dim["date"].dt.strftime("%a")
    dim["is_weekend"] = dim["day_of_week_num"] >= 6
    return dim


# Country centroids (approximate) so the Power BI map never mis-geocodes
COUNTRY_GEO = {
    "United Kingdom": ("GBR", "Europe", 54.0, -2.0), "Ireland": ("IRL", "Europe", 53.4, -8.2),
    "Germany": ("DEU", "Europe", 51.2, 10.4), "France": ("FRA", "Europe", 46.6, 2.2),
    "Netherlands": ("NLD", "Europe", 52.1, 5.3), "Spain": ("ESP", "Europe", 40.4, -3.7),
    "Switzerland": ("CHE", "Europe", 46.8, 8.2), "Belgium": ("BEL", "Europe", 50.5, 4.5),
    "Portugal": ("PRT", "Europe", 39.4, -8.2), "Australia": ("AUS", "Oceania", -25.3, 133.8),
    "Channel Islands": ("GGY", "Europe", 49.4, -2.5), "Italy": ("ITA", "Europe", 41.9, 12.6),
    "Norway": ("NOR", "Europe", 60.5, 8.5), "Sweden": ("SWE", "Europe", 60.1, 18.6),
    "Cyprus": ("CYP", "Europe", 35.1, 33.4), "Finland": ("FIN", "Europe", 61.9, 25.7),
    "Austria": ("AUT", "Europe", 47.5, 14.6), "Denmark": ("DNK", "Europe", 56.3, 9.5),
    "Greece": ("GRC", "Europe", 39.1, 21.8), "Japan": ("JPN", "Asia", 36.2, 138.3),
    "United States": ("USA", "North America", 37.1, -95.7), "Poland": ("POL", "Europe", 51.9, 19.1),
    "United Arab Emirates": ("ARE", "Middle East", 23.4, 53.8), "Israel": ("ISR", "Middle East", 31.0, 34.9),
    "Hong Kong": ("HKG", "Asia", 22.3, 114.2), "Singapore": ("SGP", "Asia", 1.35, 103.8),
    "Malta": ("MLT", "Europe", 35.9, 14.4), "Iceland": ("ISL", "Europe", 64.9, -19.0),
    "Canada": ("CAN", "North America", 56.1, -106.3), "Lithuania": ("LTU", "Europe", 55.2, 23.9),
    "South Africa": ("ZAF", "Africa", -30.6, 22.9), "Bahrain": ("BHR", "Middle East", 26.0, 50.6),
    "Brazil": ("BRA", "South America", -14.2, -51.9), "Thailand": ("THA", "Asia", 15.9, 101.0),
    "South Korea": ("KOR", "Asia", 35.9, 127.8), "Lebanon": ("LBN", "Middle East", 33.9, 35.9),
    "Bermuda": ("BMU", "North America", 32.3, -64.8), "Nigeria": ("NGA", "Africa", 9.1, 8.7),
    "Czech Republic": ("CZE", "Europe", 49.8, 15.5), "Saudi Arabia": ("SAU", "Middle East", 23.9, 45.1),
}


def build_dim_country(*frames: pd.DataFrame) -> pd.DataFrame:
    names = sorted(set().union(*[set(f["country"]) for f in frames]))
    rows = []
    for name in names:
        iso, region, lat, lon = COUNTRY_GEO.get(name, (None, "Unspecified", np.nan, np.nan))
        rows.append({"country": name, "iso3": iso, "region": region,
                     "latitude": lat, "longitude": lon,
                     "is_domestic": name == "United Kingdom"})
    return pd.DataFrame(rows)


def build_dim_customer(sales: pd.DataFrame, returns: pd.DataFrame | None = None) -> pd.DataFrame:
    known = sales[sales["customer_id"] != C.GUEST_CUSTOMER_ID]
    g = known.groupby("customer_id")
    dim = pd.DataFrame({
        "home_country": g["country"].agg(lambda s: s.value_counts().index[0]),
        "first_purchase_date": g["invoice_datetime"].min().dt.normalize(),
        "last_purchase_date": g["invoice_datetime"].max().dt.normalize(),
    }).reset_index()
    dim["cohort_month"] = dim["first_purchase_date"].dt.to_period("M").dt.to_timestamp()
    dim["is_guest"] = False
    dim["has_purchases"] = True
    frames = [dim]
    if returns is not None:
        # Customers who only appear in returns (their purchase pre-dates the data window).
        # Found when PostgreSQL's foreign-key constraint rejected their return lines.
        ret_known = returns[returns["customer_id"] != C.GUEST_CUSTOMER_ID]
        only_ret = sorted(set(ret_known["customer_id"]) - set(dim["customer_id"]))
        if only_ret:
            r = ret_known[ret_known["customer_id"].isin(only_ret)]
            frames.append(pd.DataFrame({
                "customer_id": only_ret,
                "home_country": r.groupby("customer_id")["country"].first().reindex(only_ret).values,
                "first_purchase_date": pd.NaT, "last_purchase_date": pd.NaT,
                "cohort_month": pd.NaT, "is_guest": False, "has_purchases": False}))
    dim = pd.concat(frames, ignore_index=True)
    guest = pd.DataFrame([{"customer_id": C.GUEST_CUSTOMER_ID, "home_country": "Unspecified",
                           "first_purchase_date": pd.NaT, "last_purchase_date": pd.NaT,
                           "cohort_month": pd.NaT, "is_guest": True,
                           "has_purchases": True}])
    return pd.concat([guest, dim], ignore_index=True)


def finalize_fact(frame: pd.DataFrame, id_name: str, dim_customer: pd.DataFrame | None = None) -> pd.DataFrame:
    out = frame.sort_values("invoice_datetime").reset_index(drop=True)
    out.insert(0, id_name, np.arange(1, len(out) + 1))
    out["date_key"] = out["invoice_datetime"].dt.strftime("%Y%m%d").astype(int)
    out = out.drop(columns=["description", "source_sheet"], errors="ignore")
    if dim_customer is not None:
        # months since the customer's first purchase -> drives the cohort heatmap
        cohort = dim_customer.set_index("customer_id")["cohort_month"]
        cm = out["customer_id"].map(cohort)
        inv_month = out["invoice_datetime"].dt.to_period("M").dt.to_timestamp()
        idx = (inv_month.dt.year - cm.dt.year) * 12 + (inv_month.dt.month - cm.dt.month)
        out["cohort_index"] = idx.astype("Int64")
    return out
