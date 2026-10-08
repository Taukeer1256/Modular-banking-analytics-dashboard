"""
tests/test_cleaning.py
----------------------
Unit and integration tests for data cleaning logic in data/clean_data.py.
Verifies missing field filtering, numeric coercion, positive value checks,
duplicate handling, invalid month handling, and drop logging.
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import pytest

# Ensure data/ is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "data"))

from clean_data import clean_upi, clean_rbi, drop_row, LOG_PATH


@pytest.fixture
def temp_upi_csv(tmp_path):
    """Creates a temporary CSV with known good and bad rows for UPI."""
    data = """month,year,volume_mn,value_cr,data_source,is_synthetic
Jan,2024,12203,1841000,NPCI official,FALSE
Feb,2024,12102,1828000,NPCI official,FALSE
,2024,10000,1500000,Missing Month,FALSE
Mar,,13440,1978000,Missing Year,FALSE
Apr,2024,NOT_A_NUM,1964000,Bad Volume,FALSE
May,2024,-500,2044000,Negative Volume,FALSE
Jun,2024,13890,0,Zero Value,FALSE
Jan,2024,99999,9999999,Duplicate Jan 2024,FALSE
InvalidMonth,2024,14410,2064000,Bad Month Name,FALSE
"""
    csv_file = tmp_path / "test_upi_raw.csv"
    csv_file.write_text(data, encoding="utf-8")
    return csv_file


@pytest.fixture
def temp_rbi_csv(tmp_path):
    """Creates a temporary CSV with known good and bad rows for RBI."""
    data = """system,year,volume_mn,value_cr,data_source,is_synthetic
UPI,2024,172000,247000000,RBI,FALSE
NEFT,2024,43200,4150000000,RBI,FALSE
,2024,5000,5000000,Missing System,FALSE
RTGS,,2400,2210000000,Missing Year,FALSE
IMPS,2024,0,7100000,Zero Volume,FALSE
UPI,2024,180000,250000000,Duplicate UPI 2024,FALSE
"""
    csv_file = tmp_path / "test_rbi_raw.csv"
    csv_file.write_text(data, encoding="utf-8")
    return csv_file


def test_clean_upi_drops_invalid_rows_and_logs(temp_upi_csv, tmp_path):
    """Verify that bad rows are dropped and only 2 valid rows remain."""
    out_file = tmp_path / "test_upi_clean.csv"
    cleaned = clean_upi(raw_csv_path=temp_upi_csv, out_csv_path=out_file)

    # In our fixture: 9 rows total, 2 valid (Jan 2024, Feb 2024)
    assert len(cleaned) == 2
    assert list(cleaned["month"]) == ["Jan", "Feb"]
    assert cleaned["volume_mn"].iloc[0] == 12203
    assert cleaned["value_cr"].iloc[0] == 1841000
    assert cleaned["avg_ticket_size_inr"].iloc[0] > 0
    assert out_file.exists()

    # Check log file exists and contains drop entries
    assert LOG_PATH.exists()
    log_content = LOG_PATH.read_text(encoding="utf-8")
    assert "DROP row_idx=" in log_content
    assert "missing mandatory field" in log_content


def test_clean_rbi_drops_invalid_rows(temp_rbi_csv, tmp_path):
    """Verify RBI cleaning removes duplicates, nulls, and non-positive rows."""
    out_file = tmp_path / "test_rbi_clean.csv"
    cleaned = clean_rbi(raw_csv_path=temp_rbi_csv, out_csv_path=out_file)

    # Only UPI 2024 and NEFT 2024 should survive
    assert len(cleaned) == 2
    assert set(cleaned["system"]) == {"UPI", "NEFT"}
    assert all(cleaned["volume_mn"] > 0)
    assert all(cleaned["value_cr"] > 0)


def test_production_datasets_have_no_missing_or_bad_values():
    """Verify production datasets in data/ are cleaned without any data loss."""
    upi_path = PROJECT_ROOT / "data" / "npci_upi_clean.csv"
    rbi_path = PROJECT_ROOT / "data" / "rbi_payment_systems_clean.csv"

    assert upi_path.exists(), "Clean UPI CSV must exist"
    assert rbi_path.exists(), "Clean RBI CSV must exist"

    upi_df = pd.read_csv(upi_path)
    rbi_df = pd.read_csv(rbi_path)

    assert len(upi_df) >= 30, "Should have at least 30 months of UPI data"
    assert not upi_df[["month", "year", "volume_mn", "value_cr"]].isna().any().any()
    assert (upi_df["volume_mn"] > 0).all()
    assert (upi_df["value_cr"] > 0).all()

    assert len(rbi_df) >= 10, "Should have payment system indicators"
    assert not rbi_df[["system", "year", "volume_mn", "value_cr"]].isna().any().any()
