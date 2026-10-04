# Health data generator

Synthetic data (normal distribution, simulation, not clinical data) for **every active user from the `users` table**,
sent to the backend via `POST /api/v1/health/service/ingest/{user_id}`.

## Running

1. Set the service key in `backend/.env` (without it the `/health/service/*` endpoints return 503):
   ```bash
   echo "SERVICE_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> backend/.env
   ```
2. Build and start the stack, wait for the backend:
   ```bash
   docker compose up -d --build db backend
   until curl -sf localhost:8000/health; do sleep 1; done
   ```
3. Run the generator with the same key:
   ```bash
   SERVICE_KEY=$(grep ^SERVICE_KEY= backend/.env | cut -d= -f2) \
     uv run --with httpx generator/generate.py --api http://localhost:8000 --days 7 --seed 1
   ```

Flags: `--days` (default 7: the last N UTC days **including today**, today only up to the current moment), `--seed`, `--email` (only this user; default all), `--key` (default env `SERVICE_KEY`).
Today's steps and sleep are not stored (they appear once the day is over); heart rate, stress, SpO₂, blood pressure and ECG are. Re-running during the day only appends new samples.

### Only the user `guest@example.pl`, 30 days

```bash
SERVICE_KEY=$(grep ^SERVICE_KEY= backend/.env | cut -d= -f2) \
  uv run --with httpx generator/generate.py --api http://localhost:8000 --email guest@example.pl --days 30 --seed 1
```

The account must exist (`POST /api/v1/auth/register`, password min. 8 characters, e.g. `guestguest`). Days the guest already has in the database from earlier
runs stay unchanged (writes only append), and missing ones are filled in. To start from a clean state for one user:
`DELETE FROM <table> WHERE user_id = (SELECT id FROM users WHERE email = 'guest@example.pl')` for each of the measurement tables below.

## Behavior

- A missing user profile (`sex`, `birth_date`, `weight_kg`, `height_cm`) is filled in deterministically from `(seed, user_id)`;
  an already set profile is left untouched. The cycle (`cycle_days`) is generated only for users with `sex = 'F'`.
- Idempotent: re-running with the same `--seed` does not duplicate rows.
- Heart rate and stress have a daily rhythm (lower at night).

## Database layout

Everything is tied to `users` by the foreign key `user_id → users.id` (`ON DELETE CASCADE`: deleting a user deletes their measurements).
The table split follows the shape of the data, not the metric name.

```
users 1──┬──* vital_samples            time series: heart rate, stress, SpO₂
         ├──* daily_summaries          one value per day: steps, sleep
         ├──* blood_pressure_readings  blood pressure measurement (systolic + diastolic together)
         ├──* ecg_recordings           ECG recording with waveform (JSON)
         ├──* cycle_days               cycle, one row per day (only sex = 'F')
         └──* messages                 conversation history with agents (agent module, not health data)
```

| Table | Primary key | Columns | Notes |
|---|---|---|---|
| `users` | `id` | `email` (unique), `hashed_password`, `name`, `is_active`, `created_at`, **`sex`** (`F`/`M`), **`birth_date`**, **`weight_kg`**, **`height_cm`** | Age is computed from `birth_date`; the profile is optional. |
| `vital_samples` | `(user_id, metric, ts)` | `metric` (`heart_rate` bpm, `spo2` %, `stress` 0–100), `ts` (timestamptz, UTC), `value` (float) | Heart rate and stress every 5 min, SpO₂ every 15 min (about 670 rows/day). A new metric = a new `metric` value, no migration. |
| `daily_summaries` | `(user_id, date)` | `steps`, `sleep_minutes` | Today appears only after it ends. |
| `blood_pressure_readings` | `id`, unique `(user_id, ts)` | `ts`, `systolic`, `diastolic` (mmHg) | 3 measurements per day (08:00, 14:00, 20:00). |
| `ecg_recordings` | `id`, unique `(user_id, started_at)` | `started_at`, `sample_rate_hz` (512), `avg_heart_rate`, `classification`, `samples` (JSON, about 15,000 numbers) | 1 recording per day, 30 s, simulated PQRST waveform. |
| `cycle_days` | `(user_id, date)` | `cycle_day`, `phase` (`menstrual`/`follicular`/`ovulation`/`luteal`), `cycle_length` | Only for `sex = 'F'`. |

Writes are idempotent: a primary (or unique) key conflict is skipped, so re-sending the same data duplicates nothing.
The backend adds the profile columns to the existing `users` table itself at startup (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`).
The `health_profiles` table from an earlier version is unused and can be dropped: `DROP TABLE IF EXISTS health_profiles;`.

## Checking the database

```bash
sudo docker compose exec db psql -U app -d app -c "select metric, count(*), round(avg(value)::numeric,1) from vital_samples group by metric"
sudo docker compose exec db psql -U app -d app -c "select id, email, sex, birth_date, weight_kg, height_cm from users"
```
