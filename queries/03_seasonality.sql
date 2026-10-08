-- =============================================================================
-- Query 3: Seasonality Analysis
-- Description: Groups UPI transactions across all available years by calendar month 
--              (Jan - Dec) to detect seasonal peaks, festival surges, and ticket variations.
-- Data Source: NPCI UPI Monthly Statistics
-- =============================================================================

WITH month_aggregates AS (
    SELECT
        month_num,
        month,
        COUNT(*) AS data_points,
        ROUND(AVG(volume_mn), 2) AS avg_volume_mn,
        ROUND(MIN(volume_mn), 2) AS min_volume_mn,
        ROUND(MAX(volume_mn), 2) AS max_volume_mn,
        ROUND(AVG(value_cr), 2) AS avg_value_cr,
        ROUND(AVG(avg_ticket_size_inr), 2) AS avg_ticket_size_inr
    FROM upi_monthly
    GROUP BY month_num, month
),
overall_benchmarks AS (
    SELECT 
        AVG(volume_mn) AS grand_avg_volume_mn,
        AVG(value_cr) AS grand_avg_value_cr
    FROM upi_monthly
)
SELECT
    ma.month_num,
    ma.month,
    ma.data_points,
    ma.avg_volume_mn,
    ma.min_volume_mn,
    ma.max_volume_mn,
    ma.avg_value_cr,
    ma.avg_ticket_size_inr,
    ROUND(((ma.avg_volume_mn - ob.grand_avg_volume_mn) * 100.0 / ob.grand_avg_volume_mn), 2) AS volume_seasonality_index_pct
FROM month_aggregates ma
CROSS JOIN overall_benchmarks ob
ORDER BY ma.month_num ASC;
