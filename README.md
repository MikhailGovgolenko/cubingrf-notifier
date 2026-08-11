<h1 align="center">CubingRF Notifier</h1>

<p align="center">
  <a href="https://t.me/cubingrf_notifier_bot">Open bot in Telegram</a>
</p>

<p align="center">
  <img src="assets/logo.svg" alt="cubingrf-notifier logo" width="220">
</p>

A Telegram bot that automatically tracks [cubingrf.org](https://cubingrf.org) and sends personalized notifications about speedcubing competitions.

The bot provides notifications about competition announcements, registration openings, and round results, with customizable settings for events and regions.

### Features:

- 📢 Automatic notifications about new competition announcements.
- ⏰ Customizable notifications about registration openings.
- 🏆 Upcoming CubingRF competition information.
- 📊 Notifications when round results are fully entered or edited.
- 👤 Personal round results based on an RSF ID.
- 🌍 Region-based competition filtering.
- 🧩 Discipline-based competition filtering.
- 🌐 Multilingual interface.
- ⚙️ Notification settings directly in Telegram.
- ✨ Rich formatted Telegram messages.

### How to use:

1. **Open** the bot in Telegram:
   https://t.me/cubingrf_notifier_bot

2. Press **Start** to open the bot menu.

3. Configure your preferences using:
   - `/settings` — notification settings.
   - `/competitions` — view upcoming competitions.
   - `/help` — view help information.

4. Optionally enter your **RSF ID** in the settings to receive your personal results for rounds in which you participate.

5. Receive notifications about:
   - new competition announcements;
   - registration openings;
   - completed or edited round results;
   - your personal result, attempts, average, place, and qualification for the next round.

---

### Commands:

| Command | Description |
|---------|-------------|
| `/start` | Open the main menu |
| `/settings` | Open notification settings |
| `/competitions` | Show upcoming competitions |
| `/help` | Show help information |

---

### Notification settings:

Users can customize:

- 📢 Competition announcement notifications.
- ⏰ Registration notifications.
- 📊 Round result notifications.
- 👤 RSF ID for personal results.
- 🌍 Competition regions.
- 🧩 Competition disciplines.
- ⏱️ Registration reminder interval.
- 🌐 Interface language.

The RSF ID is used only to identify the user's results. **No verification is required.**

### Round result notifications:

When results for a competition round have been entered for all participants, the bot can notify users that the round results are available.

If results for the round are edited afterwards, the bot can also send an updated notification.

For users with an RSF ID participating in the round, the notification includes:

- competition name;
- event and round;
- the user's place;
- individual attempts;
- average and best result;
- whether the user advanced to the next round.

---

The bot runs continuously in Docker with PostgreSQL as the database.

Database schema changes are managed using Alembic migrations.

---

## Safe production deployment (Docker)

The database lives in a **persistent named Docker volume**, `db-data`
(Docker volume name: `cubingrf-notifier_db-data`). All user, competition, notification, RSF ID, and result-tracking data is stored there and survives rebuilds, restarts, and VPS reboots.

### Production-safe commands

These are safe and never destroy data:

```bash
# deploy / rebuild (applies Alembic migrations automatically on container start)
docker compose up -d --build

# restart just the services (data is untouched)
docker compose restart

# inspect current health
docker compose ps
```

`web` connects to the `db` Docker service by name (`db:5432`) using the
`DATABASE_URL` in `.env`; no ports are published to the host, and the app
reaches Telegram / cubingrf.org through a normal bridge network.

### NEVER run these on the production host (data loss)

```bash
docker compose down -v      # deletes the db-data volume
docker volume rm ...        # deletes the volume
docker system prune -a      # can remove volumes/images
docker exec db psql ... -c "DROP DATABASE ...;"
DROP TABLE / TRUNCATE / destructive migrations
```

### Backup before any risky maintenance

```bash
docker compose exec db pg_dump -U cubingrf -d cubingrf -Fc -f /tmp/cubingrf.dump
docker compose cp db:/tmp/cubingrf.dump ./cubingrf-backup-$(date +%F).dump

# restore into the existing database:
docker compose exec db pg_restore -U cubingrf -d cubingrf --clean --if-exists < backup.dump
```

### Migrations

All Alembic migrations are **additive / non-destructive** on the `upgrade`
path — they create and add columns/tables only and never `DROP TABLE`,
`TRUNCATE`, or delete `users` rows.

Destructive operations only exist in `downgrade()`, which is never run by the
normal deployment process.

User creation is idempotent: `/start` looks up the user by `telegram_id` first
and never creates a duplicate.

RSF IDs are stored as user settings and do not require verification.