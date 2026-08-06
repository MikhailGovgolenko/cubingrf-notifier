<h1 align="center">CubingRF Notifier</h1>

<p align="center">
  <a href="https://t.me/cubingrf_notifier_bot">Open bot in Telegram</a>
</p>

<p align="center">
  <img src="assets/logo.svg" alt="cubingrf-notifier logo" width="220">
</p>

A Telegram bot that automatically tracks [cubingrf.org](https://cubingrf.org) and notifies users about upcoming competitions.

The bot provides competition updates, registration reminders, and customizable notification settings.

### Features:

- 🔔 Automatic notifications about new competitions.
- ⏰ Customizable registration reminders.
- 🏆 Upcoming CubingRF competition information.
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

4. Receive notifications about:
   - new competitions;
   - upcoming registration openings.

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

- 🔔 Notification types.
- 🌍 Competition regions.
- 🧩 Competition disciplines.
- ⏰ Registration reminder interval.
- 🌐 Interface language.

---

The bot runs continuously in Docker with PostgreSQL as the database.
Database schema changes are managed using Alembic migrations.
