-- =============================================================================
-- Query 4: Share by Payment Channel
-- Description: Measures market share across India's primary retail and wholesale
--              payment systems (UPI, NEFT, RTGS, IMPS, FASTag) for the latest available year.
-- Data Source: RBI Payment Systems Reports / NPCI Annual Indicators
-- =============================================================================

WITH latest_year_per_system AS (
    SELECT 
        system, 
        MAX(year) AS max_year
    FROM rbi_payment_systems
    GROUP BY system
),
latest_metrics AS (
    SELECT 
        r.system,
        r.year,
        r.volume_mn,
        r.value_cr,
        r.avg_ticket_size_inr,
        r.data_source
    FROM rbi_payment_systems r
    JOIN latest_year_per_system l 
      ON r.system = l.system AND r.year = l.max_year
),
market_totals AS (
    SELECT 
        SUM(volume_mn) AS total_market_volume_mn,
        SUM(value_cr)  AS total_market_value_cr
    FROM latest_metrics
)
SELECT
    m.system,
    m.year,
    m.volume_mn,
    ROUND(m.volume_mn * 100.0 / t.total_market_volume_mn, 2) AS volume_share_pct,
    m.value_cr,
    ROUND(m.value_cr * 100.0 / t.total_market_value_cr, 2)   AS value_share_pct,
    m.avg_ticket_size_inr,
    m.data_source
FROM latest_metrics m
CROSS JOIN market_totals t
ORDER BY m.volume_mn DESC;
