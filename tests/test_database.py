"""
tests/test_database.py
----------------------
Tests SQLite database integrity and execution of all 5 analytical queries.
"""

import glob
import sqlite3
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "banking.db"


@pytest.fixture
def db_conn():
    assert DB_PATH.exists(), "banking.db must exist before running DB tests"
    conn = sqlite3.connect(DB_PATH)
    yield conn
    conn.close()


def test_required_tables_exist(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "upi_monthly" in tables
    assert "rbi_payment_systems" in tables
    assert "banking_modules" in tables


def test_required_views_exist(db_conn):
    cursor = db_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
    views = {row[0] for row in cursor.fetchall()}
    expected_views = {
        "v_upi_yoy_growth",
        "v_upi_mom_change",
        "v_upi_seasonality",
        "v_channel_share",
        "v_opportunity_score",
    }
    assert expected_views.issubset(views)


def test_view_upi_yoy_growth(db_conn):
    df = pd.read_sql("SELECT * FROM v_upi_yoy_growth", db_conn)
    assert not df.empty
    assert "volume_yoy_pct" in df.columns
    # 2024 should have high positive YoY growth
    row_2024 = df[df["year"] == 2024]
    assert len(row_2024) == 1
    assert row_2024["volume_yoy_pct"].iloc[0] > 40.0


def test_view_upi_mom_change(db_conn):
    df = pd.read_sql("SELECT * FROM v_upi_mom_change", db_conn)
    assert len(df) >= 30
    assert "mom_volume_pct" in df.columns
    assert "mom_volume_delta_mn" in df.columns


def test_view_upi_seasonality(db_conn):
    df = pd.read_sql("SELECT * FROM v_upi_seasonality", db_conn)
    assert len(df) == 12  # 12 calendar months
    assert "seasonality_index_pct" in df.columns
    assert "avg_volume_mn" in df.columns


def test_view_channel_share(db_conn):
    df = pd.read_sql("SELECT * FROM v_channel_share", db_conn)
    assert not df.empty
    assert "volume_share_pct" in df.columns
    assert "value_share_pct" in df.columns
    # UPI should have highest volume share
    top_vol = df.iloc[0]
    assert top_vol["system"] == "UPI"
    assert top_vol["volume_share_pct"] > 60.0


def test_view_opportunity_score(db_conn):
    df = pd.read_sql("SELECT * FROM v_opportunity_score", db_conn)
    assert len(df) == 5
    assert "rank" in df.columns
    assert "baseline_opportunity_score" in df.columns
    assert df["rank"].iloc[0] == 1


def test_standalone_sql_files_execution(db_conn):
    sql_files = sorted(glob.glob(str(PROJECT_ROOT / "queries" / "*.sql")))
    assert len(sql_files) == 5, f"Expected 5 SQL files, found {len(sql_files)}"
    for sql_file in sql_files:
        content = Path(sql_file).read_text(encoding="utf-8")
        res = db_conn.execute(content).fetchall()
        assert len(res) > 0, f"Query in {sql_file} returned empty results"
