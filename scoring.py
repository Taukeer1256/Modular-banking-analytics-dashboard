"""
scoring.py
----------
Modular banking opportunity scoring engine and dynamic recommendation generator.
Evaluates candidate banking modules for small banks using multi-criteria decision analysis (MCDA).
"""

from typing import Dict, Any, Optional
import pandas as pd


DEFAULT_WEIGHTS = {
    "growth": 0.25,        # Market Growth Rate (%)
    "scale": 0.20,         # Volume / Adoption Scale
    "time_to_market": 0.25,# Implementation Speed / Ease of Launch
    "margin": 0.15,        # Margin / Unit Economics Potential
    "safety": 0.15,        # Credit Risk Safety (low default risk)
}


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """
    Normalizes a dictionary of weights so that their sum equals 1.0.
    If all weights are 0, returns equal distribution across active keys.
    """
    cleaned = {k: max(0.0, float(v)) for k, v in weights.items()}
    total = sum(cleaned.values())
    if total <= 1e-9:
        n = len(cleaned)
        return {k: 1.0 / n for k in cleaned}
    return {k: v / total for k, v in cleaned.items()}


def calculate_opportunity_scores(
    modules_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> pd.DataFrame:
    """
    Calculates composite opportunity score (0 - 100) for each banking module.
    
    Formula:
        Score = (norm_growth * w_growth) +
                (volume_scale * w_scale) +
                (time_to_market * w_ttm) +
                (margin_potential * w_margin) +
                (credit_risk_safety * w_safety)
    """
    df = modules_df.copy()
    w = normalize_weights(weights if weights is not None else DEFAULT_WEIGHTS)

    # Growth rate is in % (e.g., 45.86%), min-max scale relative to top benchmark (capped at 100)
    # 50% YoY growth maps to ~100 points
    max_growth_cap = 50.0
    df["growth_score_normalized"] = (df["market_growth_pct"] / max_growth_cap * 100.0).clip(upper=100.0, lower=0.0)

    # Calculate weighted composite score
    df["opportunity_score"] = (
        (df["growth_score_normalized"] * w.get("growth", 0.0)) +
        (df["volume_scale_score"] * w.get("scale", 0.0)) +
        (df["time_to_market_score"] * w.get("time_to_market", 0.0)) +
        (df["margin_potential_score"] * w.get("margin", 0.0)) +
        (df["credit_risk_safety_score"] * w.get("safety", 0.0))
    ).round(2)

    df["rank"] = df["opportunity_score"].rank(ascending=False, method="min").astype(int)
    df.sort_values(by="opportunity_score", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def generate_recommendation(
    scored_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None
) -> str:
    """
    Generates a dynamic, executive one-paragraph recommendation reflecting
    the top-ranked module, specific driver metrics, sensitivity to weights,
    and strategic sequencing for a small bank.
    """
    if scored_df.empty:
        return "Insufficient module data available to produce a recommendation."

    w = normalize_weights(weights if weights is not None else DEFAULT_WEIGHTS)
    top = scored_df.iloc[0]
    runner_up = scored_df.iloc[1] if len(scored_df) > 1 else None

    winner_name = top["module_name"]
    winner_score = top["opportunity_score"]
    winner_growth = top["market_growth_pct"]
    winner_ttm = top["time_to_market_score"]
    winner_safety = top["credit_risk_safety_score"]

    # Contextual driver identification
    if top["module_id"] == "MOD_PAYMENTS":
        rec = (
            f"Under your current strategic weighting, **{winner_name}** emerges as the unambiguous #1 launch priority "
            f"with an Opportunity Score of **{winner_score:.1f}/100** (runner-up: {runner_up['module_name']} at {runner_up['opportunity_score']:.1f}). "
            f"With UPI processing over 171B transactions annually and expanding at **{winner_growth:.1f}% YoY**, "
            f"instant payments serves as the lowest-friction customer acquisition hook for a small bank, combining rapid time-to-market "
            f"(score: {winner_ttm:.0f}/100 via plug-and-play switch rails) with virtually zero credit balance-sheet risk "
            f"(safety: {winner_safety:.0f}/100). While unit transaction margins are capped, deploying payments first builds essential customer "
            f"retention and transaction telemetry, creating the prerequisite behavioral data pipeline to subsequently cross-sell high-margin "
            f"credit and sticky CASA deposits."
        )
    elif top["module_id"] == "MOD_ONBOARDING":
        rec = (
            f"Based on your evaluation criteria, **{winner_name}** ranks first with a composite score of **{winner_score:.1f}/100** "
            f"(surpassing {runner_up['module_name']} at {runner_up['opportunity_score']:.1f}). "
            f"Prioritizing digital account opening leverages India's modern Aadhaar e-KYC and Account Aggregator infrastructure to rapidly "
            f"accumulate low-cost CASA deposits (growing at {winner_growth:.1f}% YoY). This provides a small bank with immediate balance-sheet "
            f"stability and lowers cost-of-funds before scaling transaction or credit modules, with minimal credit vulnerability."
        )
    elif top["module_id"] == "MOD_LENDING":
        rec = (
            f"Given your heavy emphasis on unit economics and margin capture (margin weight: {w.get('margin', 0.0)*100:.0f}%), "
            f"**{winner_name}** leads the portfolio with an Opportunity Score of **{winner_score:.1f}/100**. "
            f"Digital micro-loans deliver superior net interest margins (NIM 8-14%) and accelerated revenue generation. "
            f"However, launch caution is paramount: small banks must recognize that lending carries significant credit risk "
            f"(safety score: {top['credit_risk_safety_score']:.0f}/100) and substantial regulatory capital provisioning; "
            f"best practice suggests pairing it with or sequencing it shortly after basic KYC onboarding."
        )
    elif top["module_id"] == "MOD_DEPOSITS":
        rec = (
            f"Your risk-conservative parameters position **{winner_name}** at the top with a score of **{winner_score:.1f}/100**. "
            f"Fixed and recurring deposits yield immediate treasury liquidity and asset-liability management (ALM) predictability "
            f"with virtually zero underwriting exposure (safety: {winner_safety:.0f}/100), serving as a prudent opening salvo "
            f"for regional or risk-averse institutions seeking stable asset backing."
        )
    else:
        rec = (
            f"Based on the specified weighting matrix, **{winner_name}** achieves the highest composite rating "
            f"of **{winner_score:.1f}/100**. This module balances market expansion ({winner_growth:.1f}% YoY) with targeted institutional "
            f"capabilities, providing a dependable foundation for the institution's digital roadmap."
        )

    return rec
