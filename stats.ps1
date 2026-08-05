$sql = @"
SET TIME ZONE 'Europe/Moscow';
SET client_min_messages TO WARNING;

SELECT line
FROM (
    SELECT 1 AS sort, '==============================' AS line
    UNION ALL
    SELECT 2, '        Users statistics'
    UNION ALL
    SELECT 3, '=============================='
    UNION ALL
    SELECT 4, 'Total users:              ' || COUNT(*)::text
        FROM users
    UNION ALL
    SELECT 5, 'Notifications enabled:    ' || COUNT(*) FILTER (WHERE notifications_enabled = true)::text
        FROM users
    UNION ALL
    SELECT 6, 'Notifications disabled:   ' || COUNT(*) FILTER (WHERE notifications_enabled = false)::text
        FROM users
    UNION ALL
    SELECT 7, 'Russian users:            ' || COUNT(*) FILTER (WHERE language = 'ru')::text
        FROM users
    UNION ALL
    SELECT 8, 'English users:            ' || COUNT(*) FILTER (WHERE language = 'en')::text
        FROM users
    UNION ALL
    SELECT 9, 'With username:            ' || COUNT(*) FILTER (WHERE username IS NOT NULL AND username != '')::text
        FROM users
    UNION ALL
    SELECT 10, ''
    UNION ALL
    SELECT 11, 'First user:               ' || MIN(created_at)::text
        FROM users
    UNION ALL
    SELECT 12, 'Latest user:              ' || MAX(created_at)::text
        FROM users
    UNION ALL
    SELECT 13, ''
    UNION ALL
    SELECT 14, '=============================='
    UNION ALL
    SELECT 15, '          Users details'
    UNION ALL
    SELECT 16, '=============================='
) stats
ORDER BY sort;


SELECT
    u.created_at AS created_at,
    COALESCE(u.username, '-') AS username,
    u.telegram_id,
    u.language AS lang,
    CASE
        WHEN u.notifications_enabled THEN 'enabled'
        ELSE 'disabled'
    END AS notify,
    COUNT(DISTINCT ue.id) AS events,
    COUNT(DISTINCT ur.id) AS regions
FROM users u
LEFT JOIN user_events ue
    ON ue.user_id = u.id
LEFT JOIN user_regions ur
    ON ur.user_id = u.id
GROUP BY u.id
ORDER BY u.created_at DESC;
"@

docker exec -i cubingrf-notifier-db-1 `
    psql -U cubingrf -d cubingrf `
    --pset=footer=off `
    --quiet `
    -c "$sql"