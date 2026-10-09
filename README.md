# 🤝 HabitPact

> **Track habits. Build streaks. Stay accountable — together.**

HabitPact is a self-hosted Discord bot that helps servers build accountability communities around daily habits. Users track habits, check in daily, celebrate milestones, and compete on a leaderboard.

---

## ✨ Features

| Feature | Command |
|---|---|
| Create up to 5 habits | `/habit create <name>` |
| View all your habits | `/habit list` |
| Delete a habit (soft-delete) | `/habit delete <name>` |
| Daily check-in with streak tracking | `/checkin <habit>` |
| Personal stats across all habits | `/stats` |
| Guild accountability leaderboard | `/leaderboard` |
| Set your timezone | `/setup timezone <tz>` |
| Set a daily DM reminder | `/remind HH:MM` |
| Disable reminders | `/remind off` |

**Automatic features:**
- 🏆 Milestone celebrations at 7, 14, 30, 60, 100, 200, 365 day streaks
- 🔔 Daily DM reminders at user-configured time (timezone-aware)
- 📅 Weekly guild summary posted every Monday at 09:00 UTC

---

## 🏗️ Architecture

```
src/habitpact/
├── bot.py                # HabitPactBot: lifecycle, cog loading, slash sync
├── config.py             # Immutable Settings dataclass, dotenv loading
├── __main__.py           # Entry point: python -m habitpact
├── cogs/
│   ├── admin.py          # /setup timezone, /remind
│   ├── checkins.py       # /checkin
│   ├── habits.py         # /habit group
│   └── stats.py          # /stats, /leaderboard
├── db/
│   ├── engine.py         # Async SQLAlchemy engine lifecycle
│   └── models.py         # ORM: Guild, User, Habit, Checkin
├── scheduler/
│   └── tasks.py          # APScheduler: daily reminders + weekly reports
├── services/
│   ├── checkin_service.py   # Check-in + streak algorithm
│   ├── guild_service.py     # Guild/user get-or-create, settings
│   ├── habit_service.py     # CRUD with 5-habit limit
│   └── stats_service.py     # Personal stats + leaderboard
└── utils/
    ├── embeds.py         # Reusable Discord embed builders
    └── timezone.py       # IANA timezone validation
```

**Key design decisions:**
- **Streak computed on-the-fly**: No cached streak column — calculated from check-in dates on every query to eliminate stale state bugs
- **Guild-scoped users**: `UNIQUE(discord_id, guild_id)` — the same person can have separate habits and timezones per server
- **DB constraints enforce business rules**: One check-in per habit per day, unique habit names, all at the database level — not just application logic
- **Soft-delete habits**: `archived_at` preserves streak history after deletion

---

## 🚀 Self-Hosting Guide

### Prerequisites

- Python 3.13+
- A Discord bot application with the `bot` and `applications.commands` scopes
- (Optional) PostgreSQL for production

### Step 1 — Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. **New Application** → give it a name (e.g. "HabitPact")
3. Navigate to **Bot** → click **Reset Token** → copy the token
4. Enable **Server Members Intent** if you want display names on the leaderboard
5. Navigate to **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
6. Open the generated URL → add to your server

### Step 2 — Install

```bash
# Clone the repo
git clone https://github.com/vishalmore90/HabitPact.git
cd HabitPact

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate   # Linux/macOS

# Install
pip install -e .
```

### Step 3 — Configure

```bash
# Copy the example env file
cp .env.example .env
```

Edit `.env`:

```dotenv
# Required
DISCORD_TOKEN=your_bot_token_here

# Optional — defaults shown
DATABASE_URL=sqlite+aiosqlite:///habitpact.db
LOG_LEVEL=INFO
ENVIRONMENT=dev
```

> ⚠️ **Never commit `.env` to Git.** It is excluded by `.gitignore`.

### Step 4 — Run

```bash
python -m habitpact
```

The bot will:
1. Connect to the database (auto-creates SQLite tables on first run)
2. Load all cogs
3. Sync slash commands globally (may take up to 1 hour to propagate)
4. Start the scheduler (daily reminders + weekly reports)
5. Set its presence to `Watching your habits | /habit create`

---

## 🗄️ Database

### Development (default)

Uses SQLite with `aiosqlite`. Tables are created automatically on first run:

```
habitpact.db   ← created in the project root
```

### Production (PostgreSQL)

Set `DATABASE_URL` to a PostgreSQL async URL:

```dotenv
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/habitpact
```

> For PostgreSQL, run Alembic migrations instead of auto-create (planned for a future release).

### Schema

```
guilds          id (PK), name, joined_at
users           id (PK), discord_id, guild_id (FK), timezone, remind_at, created_at
habits          id (PK), user_id (FK), name, created_at, archived_at
checkins        id (PK), habit_id (FK), checked_date, created_at
```

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/habitpact --cov-report=term-missing

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/habitpact/
```

### Test Coverage

| Layer | Coverage |
|---|---|
| Services (habit, checkin, guild, stats) | 96–100% |
| DB models & engine | 94–97% |
| Utilities (embeds, timezone) | 100% |
| Cogs / bot / scheduler | 0% (require live Discord client) |
| **Total** | **~50%** |

---

## ⚙️ Commands Reference

### Habit Management

| Command | Description |
|---|---|
| `/habit create <name>` | Create a new habit (max 5 active, max 100 chars) |
| `/habit list` | See all your active habits with creation dates |
| `/habit delete <name>` | Archive a habit (preserves streak history) |

### Check-ins

| Command | Description |
|---|---|
| `/checkin <habit>` | Check in for today. Shows current streak, best streak, total check-ins |

Milestones are celebrated automatically at: **7 · 14 · 30 · 60 · 100 · 200 · 365** days.

### Stats & Leaderboard

| Command | Description |
|---|---|
| `/stats` | Your personal habits with 🔥 flame indicators (ephemeral) |
| `/leaderboard` | Top 10 guild members by total active streak days |

### Settings

| Command | Description |
|---|---|
| `/setup timezone <tz>` | Set your [IANA timezone](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) for accurate streak tracking |
| `/remind HH:MM` | Set a daily DM reminder at HH:MM in your timezone |
| `/remind off` | Disable daily reminders |

---

## 🔐 Security

- **Bot token** is loaded from environment variables only — never hardcoded
- **`.env` is excluded from Git** via `.gitignore`
- **`.env.example`** is committed as a safe template
- All user input is validated before reaching the database
- Errors are always sent as **ephemeral** (private) messages — sensitive data never leaks to public channels

---

## 📋 Git History

```
7dccfca  test: expand coverage — embeds, engine lifecycle, scheduler logic
47548ea  feat(scheduler): APScheduler daily reminders and weekly reports
2630d65  feat(cogs): AdminCog — /setup timezone and /remind
f8bd897  feat(cogs): StatsService + /stats and /leaderboard
6bc61cf  feat(cogs): CheckinCog — streak display and milestone celebrations
56c1811  feat(bot): bot core, habit cog, embed utilities, entry point
cf903a2  feat(services): GuildService, HabitService, CheckinService + streak algorithm
4738b55  feat(db): SQLAlchemy async ORM models and engine lifecycle
aea4968  chore: bootstrap project structure, config loader, and tooling
```

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

## 🛠️ Built With

- [discord.py](https://github.com/Rapptz/discord.py) — Discord API wrapper
- [SQLAlchemy](https://www.sqlalchemy.org/) (async) — ORM and database layer
- [aiosqlite](https://github.com/omnilib/aiosqlite) — Async SQLite driver
- [APScheduler](https://apscheduler.readthedocs.io/) — Background task scheduler
- [python-dotenv](https://github.com/theskumar/python-dotenv) — `.env` file loading
- [Alembic](https://alembic.sqlalchemy.org/) — Database migrations (production)
