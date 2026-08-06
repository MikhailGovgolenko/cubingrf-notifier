$sqlStats = @"
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
    SELECT 4, 'Total users (active):    ' || COUNT(*) FILTER (WHERE blocked_at IS NULL)::text
        FROM users
    UNION ALL
    SELECT 5, 'Blocked users:            ' || COUNT(*) FILTER (WHERE blocked_at IS NOT NULL)::text
        FROM users
    UNION ALL
    SELECT 6, 'Notifications enabled:    ' || COUNT(*) FILTER (WHERE notifications_enabled = true)::text
        FROM users
    UNION ALL
    SELECT 7, 'Notifications disabled:   ' || COUNT(*) FILTER (WHERE notifications_enabled = false)::text
        FROM users
    UNION ALL
    SELECT 8, 'Russian users:            ' || COUNT(*) FILTER (WHERE language = 'ru')::text
        FROM users
    UNION ALL
    SELECT 9, 'English users:            ' || COUNT(*) FILTER (WHERE language = 'en')::text
        FROM users
    UNION ALL
    SELECT 10, 'With username:            ' || COUNT(*) FILTER (WHERE username IS NOT NULL AND username != '')::text
        FROM users
    UNION ALL
    SELECT 11, 'Active last 24h:          ' || COUNT(*) FILTER (WHERE last_seen_at IS NOT NULL AND last_seen_at >= NOW() - INTERVAL '24 hours')::text
        FROM users
    UNION ALL
    SELECT 12, 'Active last 7 days:       ' || COUNT(*) FILTER (WHERE last_seen_at IS NOT NULL AND last_seen_at >= NOW() - INTERVAL '7 days')::text
        FROM users
    UNION ALL
    SELECT 13, 'Active last 30 days:      ' || COUNT(*) FILTER (WHERE last_seen_at IS NOT NULL AND last_seen_at >= NOW() - INTERVAL '30 days')::text
        FROM users
    UNION ALL
    SELECT 14, 'Never seen:               ' || COUNT(*) FILTER (WHERE last_seen_at IS NULL)::text
        FROM users
    UNION ALL
    SELECT 15, ''
    UNION ALL
    SELECT 16, 'First user:               ' || to_char(MIN(created_at), 'YYYY-MM-DD HH24:MI:SSOF')
        FROM users
    UNION ALL
    SELECT 17, 'Latest user:              ' || to_char(MAX(created_at), 'YYYY-MM-DD HH24:MI:SSOF')
        FROM users
    UNION ALL
    SELECT 18, ''
    UNION ALL
    SELECT 19, '=============================='
    UNION ALL
    SELECT 20, '          Users details'
    UNION ALL
    SELECT 21, '=============================='
    UNION ALL
    SELECT 22, ''
    UNION ALL
    SELECT 23, '=============================='
    UNION ALL
    SELECT 24, '          Blocked users'
    UNION ALL
    SELECT 25, '=============================='
) stats
ORDER BY sort;
"@

$sqlUsers = @"
SET TIME ZONE 'Europe/Moscow';

SELECT
    to_char(u.created_at, 'YYYY-MM-DD HH24:MI:SSOF') AS created_at,
    CASE
        WHEN u.last_seen_at IS NULL THEN ''
        ELSE to_char(u.last_seen_at, 'YYYY-MM-DD HH24:MI:SSOF')
    END AS last_seen_at,
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
WHERE u.blocked_at IS NULL
GROUP BY u.id
ORDER BY u.created_at DESC;
"@

$sqlBlocked = @"
SET TIME ZONE 'Europe/Moscow';

SELECT
    to_char(u.blocked_at, 'YYYY-MM-DD HH24:MI:SSOF') AS blocked_at,
    COALESCE(u.username, '-') AS username,
    u.telegram_id,
    u.language AS lang
FROM users u
WHERE u.blocked_at IS NOT NULL
ORDER BY u.blocked_at DESC;
"@

docker exec -i cubingrf-notifier-db-1 `
    psql -U cubingrf -d cubingrf `
    --pset=footer=off `
    --pset=tuples_only=on `
    --quiet `
    -c "$sqlStats"

docker exec -i cubingrf-notifier-db-1 `
    psql -U cubingrf -d cubingrf `
    --pset=footer=off `
    --quiet `
    -c "$sqlUsers"

docker exec -i cubingrf-notifier-db-1 `
    psql -U cubingrf -d cubingrf `
    --pset=footer=off `
    --pset=tuples_only=on `
    --quiet `
    -c "$sqlBlocked"