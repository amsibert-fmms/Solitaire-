-- Derive canonical difficulty summaries per deck key and draw mode.
PRAGMA create_agg_tables=1;

WITH thresholds AS (
    SELECT
        draw_mode,
        percentile_cont(0.30) WITHIN GROUP (ORDER BY difficulty_score) AS p30,
        percentile_cont(0.70) WITHIN GROUP (ORDER BY difficulty_score) AS p70
    FROM wins
    WHERE difficulty_score IS NOT NULL
    GROUP BY draw_mode
),
base AS (
    SELECT
        deck_key,
        draw_mode,
        median(node_count) AS median_nodes,
        median(solve_time_ms) AS median_time,
        median(difficulty_score) AS median_difficulty
    FROM wins
    WHERE difficulty_score IS NOT NULL
    GROUP BY deck_key, draw_mode
)
CREATE OR REPLACE TABLE deck_summary AS
SELECT
    b.deck_key,
    b.draw_mode,
    b.median_nodes,
    b.median_time,
    b.median_difficulty,
    CASE
        WHEN b.median_difficulty IS NULL THEN NULL
        WHEN t.p30 IS NULL OR t.p70 IS NULL THEN 'medium'
        WHEN b.median_difficulty < t.p30 THEN 'easy'
        WHEN b.median_difficulty > t.p70 THEN 'hard'
        ELSE 'medium'
    END AS difficulty_level
FROM base AS b
LEFT JOIN thresholds AS t USING (draw_mode);

CREATE INDEX IF NOT EXISTS idx_deck_summary_deck_key ON deck_summary(deck_key);
CREATE INDEX IF NOT EXISTS idx_deck_summary_draw_mode ON deck_summary(draw_mode);
