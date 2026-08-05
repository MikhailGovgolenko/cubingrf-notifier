<h1 align="center">cubingRF Notifier</h1>

<p align="center">
  <a href="https://t.me/cubingrf_notifier_bot">Open bot in Telegram</a>
</p>


<p align="center">
  <img src="assets/logo.svg" alt="cubingrf-notifier logo" width="220">
</p>

A Telegram bot that automatically tracks speedcubing competitions on
[cubingrf.org](https://cubingrf.org) and notifies subscribed users about new events.

The bot provides competition updates, registration reminders, and customizable notification settings.


### Features:

- 🔔 Automatic notifications about new competitions.
- 🏆 Information about upcoming CubingRF events.
- ⏰ Registration reminders.
- 🌍 Region-based competition filtering.
- ⚙️ Notification settings directly in Telegram.

### How to use:

1. **Open** the bot in Telegram:
   https://t.me/cubingrf_notifier_bot

2. Press **Start** to subscribe to notifications.

3. Configure your preferences using:
   - `/settings` — notification settings.
   - `/competitions` — upcoming competitions.
   - `/status` — subscription status.

4. Receive notifications about new competitions automatically.

---

### Commands:

| Command | Description |
|---------|-------------|
| `/start` | Subscribe to notifications |
| `/stop` | Unsubscribe from notifications |
| `/status` | Check subscription status |
| `/settings` | Open settings menu |
| `/competitions` | Show upcoming competitions |
| `/help` | Show available commands |

---

The bot runs continuously using Docker and PostgreSQL, with database migrations managed automatically through Alembic.
