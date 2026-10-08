-- =============================================================================
-- Query 5: Opportunity Score Query for Modular Banking Architecture
-- Description: Multi-criteria decision analysis (MCDA) in SQL evaluating 
--              which banking module a small bank should launch first.
--
-- Evaluated Modules:
--   1. UPI & Instant Payments
--   2. Digital Onboarding & CASA
--   3. Digital MSME & Micro-Lending
--   4. RuPay Debit & Merchant POS
--   5. Fixed Deposits & Term Savings
--
-- Scoring Dimensions (0 - 100):
--   - Market Growth Rate (w=0.25)
--   - Adoption Scale / Volume Potential (w=0.20)
--   - Time to Market / Speed of Launch (w=0.25)
--   - Unit Margin Potential (w=0.15)
--   - Credit Risk Safety (w=0.15)
-- =============================================================================

WITH scored_modules AS (
    SELECT
        module_id,
        module_name,
        category,
        market_growth_pct,
        volume_scale_score,
        time_to_market_score,
        margin_potential_score,
        credit_risk_safety_score,
        capital_expenditure_score,
        ROUND(
            (market_growth_pct * 0.25) +
            (volume_scale_score * 0.20) +
            (time_to_market_score * 0.25) +
            (margin_potential_score * 0.15) +
            (credit_risk_safety_score * 0.15),
            2
        ) AS opportunity_score,
        data_source,
        is_synthetic,
        description
    FROM banking_modules
)
SELECT
    DENSE_RANK() OVER (ORDER BY opportunity_score DESC) AS rank,
    module_name,
    category,
    opportunity_score,
    market_growth_pct AS market_growth_rate_pct,
    volume_scale_score,
    time_to_market_score,
    margin_potential_score,
    credit_risk_safety_score,
    capital_expenditure_score,
    data_source,
    description
FROM scored_modules
ORDER BY opportunity_score DESC;
