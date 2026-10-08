-- =============================================================================
-- Query 2: Month-over-Month (MoM) Change
-- Description: Analyzes chronological sequence of UPI volume and value using 
--              window LAG() functions to compute consecutive monthly variance.
-- Data Source: NPCI UPI Monthly Statistics
-- =============================================================================

SELECT
    period,
    year,
    month,
    volume_mn,
    LAG(volume_mn) OVER (ORDER BY period) AS prev_volume_mn,
    ROUND(volume_mn - LAG(volume_mn) OVER (ORDER BY period), 2) AS mom_volume_delta_mn,
    ROUND(
        (volume_mn - LAG(volume_mn) OVER (ORDER BY period)) * 100.0 
        / LAG(volume_mn) OVER (ORDER BY period), 
        2
    ) AS mom_volume_pct,
    value_cr,
    LAG(value_cr) OVER (ORDER BY period) AS prev_value_cr,
    ROUND(value_cr - LAG(value_cr) OVER (ORDER BY period), 2) AS mom_value_delta_cr,
    ROUND(
        (value_cr - LAG(value_cr) OVER (ORDER BY period)) * 100.0 
        / LAG(value_cr) OVER (ORDER BY period), 
        2
    ) AS mom_value_pct,
    avg_ticket_size_inr,
    is_synthetic
FROM upi_monthly
ORDER BY period ASC;
