-- Update discipline_analytics view to include salary statistics
CREATE OR REPLACE VIEW discipline_analytics AS
SELECT
    discipline,
    COUNT(*) as graduate_positions,
    AVG(grad_confidence) as avg_grad_confidence,
    AVG(discipline_confidence) as avg_discipline_confidence,
    COUNT(*) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as graduate_positions_with_salary,
    -- Add salary statistics
    AVG(CASE
        WHEN salary ~ '^\$?[\d,]+(\.\d{2})?$' THEN
            CAST(REPLACE(REPLACE(salary, '$', ''), ',', '') AS NUMERIC)
        WHEN salary ~ '^\$?[\d,]+\s*-\s*\$?[\d,]+$' THEN
            (CAST(REPLACE(REPLACE(SPLIT_PART(salary, '-', 1), '$', ''), ',', '') AS NUMERIC) +
             CAST(REPLACE(REPLACE(SPLIT_PART(salary, '-', 2), '$', ''), ',', '') AS NUMERIC)) / 2
        ELSE NULL
    END) FILTER (WHERE salary IS NOT NULL AND salary != '' AND salary != 'none') as avg_salary,
    array_agg(DISTINCT unnest(discipline_keywords)) FILTER (WHERE discipline_keywords IS NOT NULL) as all_keywords
FROM jobs
WHERE discipline IS NOT NULL AND discipline != 'Unknown' AND is_graduate_position = true
GROUP BY discipline
ORDER BY graduate_positions DESC;
