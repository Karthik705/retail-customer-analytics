-- =====================================================================
-- 01_create_schema.sql
-- Star schema for the Online Retail II analytics warehouse (PostgreSQL)
-- Run:  psql -d retail -f sql/01_create_schema.sql
-- =====================================================================

DROP SCHEMA IF EXISTS retail CASCADE;
CREATE SCHEMA retail;
SET search_path TO retail;

-- ---------------------------------------------------------- dimensions
CREATE TABLE dim_date (
    date_value        DATE        NOT NULL UNIQUE,
    date_key          INTEGER     PRIMARY KEY,          -- YYYYMMDD
    year              SMALLINT    NOT NULL,
    quarter           CHAR(2)     NOT NULL,
    month_num         SMALLINT    NOT NULL,
    month_name        CHAR(3)     NOT NULL,
    year_month        CHAR(7)     NOT NULL,
    week_of_year      SMALLINT    NOT NULL,
    day_of_week_num   SMALLINT    NOT NULL,             -- 1 = Monday
    day_name          CHAR(3)     NOT NULL,
    is_weekend        BOOLEAN     NOT NULL
);

CREATE TABLE dim_country (
    country           VARCHAR(40) PRIMARY KEY,
    iso3              CHAR(3),
    region            VARCHAR(20) NOT NULL,
    latitude          NUMERIC(7,3),
    longitude         NUMERIC(7,3),
    is_domestic       BOOLEAN     NOT NULL
);

CREATE TABLE dim_product (
    stock_code        VARCHAR(20)  PRIMARY KEY,
    description       VARCHAR(100) NOT NULL,
    category          VARCHAR(30)  NOT NULL,
    median_unit_price NUMERIC(10,2)
);

CREATE TABLE dim_customer (
    customer_id         INTEGER     PRIMARY KEY,        -- 0 = guest / unknown
    home_country        VARCHAR(40) REFERENCES dim_country(country),
    first_purchase_date DATE,
    last_purchase_date  DATE,
    cohort_month        DATE,
    is_guest            BOOLEAN     NOT NULL,
    has_purchases       BOOLEAN     NOT NULL            -- FALSE = return-only customer
);

-- ---------------------------------------------------------- facts
CREATE TABLE fact_sales (
    sales_line_id     INTEGER       PRIMARY KEY,
    invoice_no        VARCHAR(10)   NOT NULL,
    stock_code        VARCHAR(20)   NOT NULL REFERENCES dim_product(stock_code),
    quantity          INTEGER       NOT NULL CHECK (quantity > 0),
    invoice_datetime  TIMESTAMP     NOT NULL,
    unit_price        NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    customer_id       INTEGER       NOT NULL REFERENCES dim_customer(customer_id),
    country           VARCHAR(40)   NOT NULL REFERENCES dim_country(country),
    line_value        NUMERIC(12,2) NOT NULL,
    date_key          INTEGER       NOT NULL REFERENCES dim_date(date_key),
    cohort_index      SMALLINT                          -- months since first purchase
);

CREATE TABLE fact_returns (
    return_line_id    INTEGER       PRIMARY KEY,
    invoice_no        VARCHAR(10)   NOT NULL,
    stock_code        VARCHAR(20)   NOT NULL REFERENCES dim_product(stock_code),
    quantity          INTEGER       NOT NULL,           -- stored as positive units returned
    invoice_datetime  TIMESTAMP     NOT NULL,
    unit_price        NUMERIC(10,2) NOT NULL,
    customer_id       INTEGER       NOT NULL REFERENCES dim_customer(customer_id),
    country           VARCHAR(40)   NOT NULL REFERENCES dim_country(country),
    line_value        NUMERIC(12,2) NOT NULL,
    date_key          INTEGER       NOT NULL REFERENCES dim_date(date_key)
);

CREATE TABLE fact_fees (
    fee_line_id       INTEGER       PRIMARY KEY,
    invoice_no        VARCHAR(10)   NOT NULL,
    stock_code        VARCHAR(20)   NOT NULL,           -- POST, DOT, M, AMAZONFEE, ...
    quantity          INTEGER       NOT NULL,
    invoice_datetime  TIMESTAMP     NOT NULL,
    unit_price        NUMERIC(12,2) NOT NULL,
    customer_id       INTEGER       NOT NULL,
    country           VARCHAR(40)   NOT NULL,
    line_value        NUMERIC(12,2) NOT NULL,
    date_key          INTEGER       NOT NULL
);

-- ---------------------------------------------------------- model output (from notebook 04)
CREATE TABLE customer_insights (
    customer_id              INTEGER PRIMARY KEY REFERENCES dim_customer(customer_id),
    recency_days             INTEGER,
    frequency                INTEGER,
    gross_sales              NUMERIC(12,2),
    returns_value            NUMERIC(12,2),
    monetary                 NUMERIC(12,2),
    r_score                  SMALLINT,
    f_score                  SMALLINT,
    m_score                  SMALLINT,
    rfm_score                CHAR(3),
    segment                  VARCHAR(30),
    recommended_action       TEXT,
    churn_probability        NUMERIC(6,4),
    risk_tier                VARCHAR(20),
    expected_quarterly_spend NUMERIC(12,2),
    annual_value             NUMERIC(12,2),
    revenue_at_risk_90d      NUMERIC(12,2),
    target_for_campaign      BOOLEAN,
    campaign_tier            VARCHAR(30),
    expected_recovery        NUMERIC(12,2),
    recency_vs_gap           NUMERIC(10,4),
    distinct_categories      SMALLINT
);

-- ---------------------------------------------------------- indexes for common filters/joins
CREATE INDEX ix_sales_date      ON fact_sales (date_key);
CREATE INDEX ix_sales_customer  ON fact_sales (customer_id);
CREATE INDEX ix_sales_product   ON fact_sales (stock_code);
CREATE INDEX ix_sales_invoice   ON fact_sales (invoice_no);
CREATE INDEX ix_returns_date    ON fact_returns (date_key);
CREATE INDEX ix_returns_cust    ON fact_returns (customer_id);
