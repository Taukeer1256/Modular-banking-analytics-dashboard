"""
tests/test_scoring.py
---------------------
Unit tests for the scoring model and dynamic recommendation logic in scoring.py.
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "data"))

from scoring import (
    DEFAULT_WEIGHTS,
    normalize_weights,
    calculate_opportunity_scores,
    generate_recommendation,
)
from clean_data import get_banking_modules_benchmark


@pytest.fixture
def sample_modules_df():
    return get_banking_modules_benchmark()


def test_normalize_weights_default():
    w = normalize_weights(DEFAULT_WEIGHTS)
    assert pytest.approx(sum(w.values()), 1e-6) == 1.0
    for val in w.values():
        assert val >= 0.0


def test_normalize_weights_custom():
    custom = {"growth": 10, "scale": 10, "time_to_market": 10, "margin": 10, "safety": 10}
    norm = normalize_weights(custom)
    for v in norm.values():
        assert pytest.approx(v, 1e-6) == 0.2


def test_normalize_weights_all_zeros():
    zeros = {"growth": 0, "scale": 0, "time_to_market": 0, "margin": 0, "safety": 0}
    norm = normalize_weights(zeros)
    assert pytest.approx(sum(norm.values()), 1e-6) == 1.0
    assert norm["growth"] == 0.2


def test_calculate_opportunity_scores_default(sample_modules_df):
    scored = calculate_opportunity_scores(sample_modules_df, DEFAULT_WEIGHTS)
    assert "opportunity_score" in scored.columns
    assert "rank" in scored.columns
    assert len(scored) == len(sample_modules_df)

    # Top module should be rank 1 with highest score
    assert scored.iloc[0]["rank"] == 1
    assert scored.iloc[0]["opportunity_score"] >= scored.iloc[-1]["opportunity_score"]
    # Payments should rank #1 with default weights
    assert scored.iloc[0]["module_id"] == "MOD_PAYMENTS"


def test_scoring_sensitivity_margin_dominant(sample_modules_df):
    """When margin is the sole priority (100%), Lending should jump to #1."""
    margin_weights = {
        "growth": 0.0,
        "scale": 0.0,
        "time_to_market": 0.0,
        "margin": 1.0,
        "safety": 0.0,
    }
    scored = calculate_opportunity_scores(sample_modules_df, margin_weights)
    assert scored.iloc[0]["module_id"] == "MOD_LENDING"
    assert scored.iloc[0]["rank"] == 1


def test_scoring_sensitivity_safety_dominant(sample_modules_df):
    """When safety is dominant, zero credit risk modules (Payments/Onboarding) win."""
    safety_weights = {
        "growth": 0.0,
        "scale": 0.0,
        "time_to_market": 0.0,
        "margin": 0.0,
        "safety": 1.0,
    }
    scored = calculate_opportunity_scores(sample_modules_df, safety_weights)
    top_id = scored.iloc[0]["module_id"]
    assert top_id in ["MOD_PAYMENTS", "MOD_ONBOARDING"]


def test_generate_recommendation_text(sample_modules_df):
    scored = calculate_opportunity_scores(sample_modules_df, DEFAULT_WEIGHTS)
    rec = generate_recommendation(scored, DEFAULT_WEIGHTS)

    assert isinstance(rec, str)
    assert len(rec) > 100
    assert "UPI & Instant Payments" in rec
    assert "Opportunity Score" in rec
    assert "YoY" in rec
