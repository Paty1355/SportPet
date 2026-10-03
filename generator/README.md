# Generator danych zdrowotnych

Syntetyczne dane (rozkład normalny, symulacja, nie dane kliniczne) dla **każdego aktywnego użytkownika z tabeli `users`**,
wysyłane do backendu przez `POST /api/v1/health/service/ingest/{user_id}`.

## Uruchomienie

1. Ustaw klucz serwisowy w `backend/.env` (bez niego endpointy `/health/service/*` zwracają 503):
   ```bash
   echo "SERVICE_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" >> backend/.env
   ```
2. Zbuduj i uruchom stack, poczekaj na backend:
   ```bash
   docker compose up -d --build db backend
   until curl -sf localhost:8000/health; do sleep 1; done
   ```
3. Uruchom generator z tym samym kluczem:
   ```bash
   SERVICE_KEY=$(grep ^SERVICE_KEY= backend/.env | cut -d= -f2) \
     uv run --with httpx generator/generate.py --api http://localhost:8000 --days 7 --seed 1
   ```

Flagi: `--days` (domyślnie 7: ostatnie N dób UTC **włącznie z dzisiejszą**, dzisiaj tylko do bieżącej chwili), `--seed`, `--email` (tylko ten użytkownik; domyślnie wszyscy), `--key` (domyślnie env `SERVICE_KEY`).
Dzisiejsze kroki i sen nie są zapisywane (pojawią się, gdy doba się skończy); puls, stres, SpO₂, ciśnienie i ECG tak. Ponowne uruchomienie w ciągu dnia dopisuje tylko nowe próbki.

### Tylko użytkownik `guest@example.pl`, 30 dni

```bash
SERVICE_KEY=$(grep ^SERVICE_KEY= backend/.env | cut -d= -f2) \
  uv run --with httpx generator/generate.py --api http://localhost:8000 --email guest@example.pl --days 30 --seed 1
```

Konto musi istnieć (`POST /api/v1/auth/register`, hasło min. 8 znaków, np. `guestguest`). Dni, które gość ma już w bazie z wcześniejszych
uruchomień, zostają bez zmian (zapis tylko dopisuje), a brakujące są uzupełniane. Żeby zacząć od czystego stanu dla jednego użytkownika:
`DELETE FROM <tabela> WHERE user_id = (SELECT id FROM users WHERE email = 'guest@example.pl')` dla każdej z tabel pomiarów poniżej.

## Zachowanie

- Brakujący profil użytkownika (`sex`, `birth_date`, `weight_kg`, `height_cm`) jest uzupełniany deterministycznie z `(seed, user_id)`;
  już ustawiony profil zostaje nietknięty. Cykl (`cycle_days`) dostają tylko użytkownicy z `sex = 'F'`.
- Idempotentne: ponowne uruchomienie z tym samym `--seed` nie dubluje wierszy.
- Puls i stres mają rytm dobowy (niżej w nocy).

## Jak wygląda baza

Wszystko jest powiązane z `users` kluczem obcym `user_id → users.id` (`ON DELETE CASCADE`: usunięcie użytkownika kasuje jego pomiary).
Podział tabel wynika z kształtu danych, nie z nazwy metryki.

```
users 1──┬──* vital_samples            szereg czasowy: puls, stres, SpO₂
         ├──* daily_summaries          jedna wartość na dzień: kroki, sen
         ├──* blood_pressure_readings  pomiar ciśnienia (skurczowe + rozkurczowe razem)
         ├──* ecg_recordings           nagranie EKG z falą (JSON)
         ├──* cycle_days               cykl, jeden wiersz na dzień (tylko sex = 'F')
         └──* messages                 historia rozmów z agentami (moduł agentów, nie dane zdrowotne)
```

| Tabela | Klucz główny | Kolumny | Uwagi |
|---|---|---|---|
| `users` | `id` | `email` (unikalny), `hashed_password`, `name`, `is_active`, `created_at`, **`sex`** (`F`/`M`), **`birth_date`**, **`weight_kg`**, **`height_cm`** | Wiek liczony z `birth_date`; profil jest opcjonalny. |
| `vital_samples` | `(user_id, metric, ts)` | `metric` (`heart_rate` bpm, `spo2` %, `stress` 0–100), `ts` (timestamptz, UTC), `value` (float) | Puls i stres co 5 min, SpO₂ co 15 min (ok. 670 wierszy/dobę). Nowa metryka = nowa wartość `metric`, bez migracji. |
| `daily_summaries` | `(user_id, date)` | `steps`, `sleep_minutes` | Dzisiejsza doba pojawia się dopiero po jej zakończeniu. |
| `blood_pressure_readings` | `id`, unikalne `(user_id, ts)` | `ts`, `systolic`, `diastolic` (mmHg) | 3 pomiary na dobę (08:00, 14:00, 20:00). |
| `ecg_recordings` | `id`, unikalne `(user_id, started_at)` | `started_at`, `sample_rate_hz` (512), `avg_heart_rate`, `classification`, `samples` (JSON, ok. 15 000 liczb) | 1 nagranie na dobę, 30 s, symulowana fala PQRST. |
| `cycle_days` | `(user_id, date)` | `cycle_day`, `phase` (`menstrual`/`follicular`/`ovulation`/`luteal`), `cycle_length` | Tylko dla `sex = 'F'`. |

Zapis jest idempotentny: konflikt klucza głównego (lub unikalnego) jest pomijany, więc ponowne wysłanie tych samych danych niczego nie dubluje.
Kolumny profilu w istniejącej tabeli `users` backend dokłada sam przy starcie (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`).
Tabela `health_profiles` z wcześniejszej wersji jest nieużywana i można ją usunąć: `DROP TABLE IF EXISTS health_profiles;`.

## Sprawdzenie w bazie

```bash
sudo docker compose exec db psql -U app -d app -c "select metric, count(*), round(avg(value)::numeric,1) from vital_samples group by metric"
sudo docker compose exec db psql -U app -d app -c "select id, email, sex, birth_date, weight_kg, height_cm from users"
```
