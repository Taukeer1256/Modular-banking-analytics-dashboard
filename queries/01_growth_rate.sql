-- =============================================================================
-- Query 1: Annual Year-over-Year (YoY) Growth Rate
-- Description: Aggregates UPI monthly statistics by year and calculates YoY 
--              growth percentage for both transaction volume (Mn) and value (Cr).
-- Data Source: NPCI UPI Monthly Statistics / PIB Releases
-- =============================================================================

WITH yearly_summary AS (
    SELECT 
        year,
        COUNT(*) AS months_counted,
        SUM(volume_mn) AS total_volume_mn,
        SUM(value_cr) AS total_value_cr,
        ROUND(SUM(value_cr) * 10.0 / SUM(volume_mn), 2) AS avg_ticket_size_inr
    FROM upi_monthly
    GROUP BY year
)
SELECT
    curr.year,
    curr.months_counted,
    curr.total_volume_mn,
    prev.total_volume_mn AS prev_year_volume_mn,
    ROUND(
        (curr.total_volume_mn - prev.total_volume_mn) * 100.0 / prev.total_volume_mn, 
        2
    ) AS volume_yoy_pct,
    curr.total_value_cr,
    prev.total_value_cr AS prev_year_value_cr,
    ROUND(
        (curr.total_value_cr - prev.total_value_cr) * 100.0 / prev.total_value_cr, 
        2
    ) AS value_yoy_pct,
    curr.avg_ticket_size_inr
FROM yearly_summary curr
LEFT JOIN yearly_summary prev ON curr.year = prev.year + 1
ORDER BY curr.year ASC;
