"""Central configuration: paths, business rules and analysis parameters.

Keeping every assumption in one file makes the analysis reproducible and
makes every decision easy to trace and change.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
IMAGES_DIR = ROOT / "images"
OUTPUTS_DIR = ROOT / "outputs"
REPORTS_DIR = ROOT / "reports"

RAW_FILE_CANDIDATES = [
    RAW_DIR / "online_retail_II.xlsx",   # original UCI file
    RAW_DIR / "online_retail_II.xlsb",   # binary Excel mirror
]

# ---------------------------------------------------------------- source data
SHEETS = ["Year 2009-2010", "Year 2010-2011"]
# The two sheets overlap: both contain 2010-12-01 .. 2010-12-09.
# We keep the overlap rows from the second sheet only.
SHEET_OVERLAP_START = "2010-12-01"

# Stock codes that are not products (postage, fees, manual adjustments, vouchers...)
NON_PRODUCT_CODES = {
    "POST", "DOT", "M", "C2", "D", "S", "BANK CHARGES", "ADJUST", "ADJUST2",
    "AMAZONFEE", "PADS", "B", "CRUK", "TEST001", "TEST002",
}
NON_PRODUCT_PREFIXES = ("gift_", "TEST")

GUEST_CUSTOMER_ID = 0  # surrogate key for transactions without a Customer ID

COUNTRY_FIXES = {
    "EIRE": "Ireland",
    "RSA": "South Africa",
    "USA": "United States",
    "Korea": "South Korea",
    "European Community": "Unspecified",
    "West Indies": "Unspecified",
}

# ---------------------------------------------------------------- analysis
CURRENCY = "£"
CHURN_WINDOW_DAYS = 90          # churned = no purchase in the next 90 days
ACTIVE_LOOKBACK_DAYS = 365      # population = customers who bought in the last 12 months
TRAIN_SNAPSHOTS = ["2010-09-10", "2010-12-10", "2011-03-11", "2011-06-10"]
TEST_SNAPSHOT = "2011-09-10"    # out-of-time test: label window ends 2011-12-09
SCORING_DATE = "2011-12-10"     # "today" for the final risk scores
RANDOM_STATE = 42

# Retention-campaign assumptions (see reports/business_recommendations.md)
CAMPAIGN_SAVE_RATE = 0.15       # share of targeted would-be churners retained
CAMPAIGN_COST_PER_CUSTOMER = 10.0   # £ voucher + outreach cost
REVENUE_HORIZON_DAYS = 90       # recovered revenue counted over the churn window only (conservative)
