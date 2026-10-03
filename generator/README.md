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

Flagi: `--days` (domyślnie 7: ostatnie N dób UTC **włącznie z dzisiejszą**, dzisiaj tylko do bieżącej chwili), `--seed`, `--key` (domyślnie env `SERVICE_KEY`).
Dzisiejsze kroki i sen nie są zapisywane (pojawią się, gdy doba się skończy); puls, stres, SpO₂, ciśnienie i ECG tak. Ponowne uruchomienie w ciągu dnia dopisuje tylko nowe próbki.

## Zachowanie

- Brakujący profil użytkownika (`sex`, `birth_date`, `weight_kg`, `height_cm`) jest uzupełniany deterministycznie z `(seed, user_id)`;
  już ustawiony profil zostaje nietknięty. Cykl (`cycle_days`) dostają tylko użytkownicy z `sex = 'F'`.
- Idempotentne: ponowne uruchomienie z tym samym `--seed` nie dubluje wierszy.
- Puls i stres mają rytm dobowy (niżej w nocy).

## Schemat

`users` (profil: `sex`, `birth_date`, `weight_kg`, `height_cm`; wiek liczony z `birth_date`), `vital_samples` (heart_rate, stress, spo2),
`daily_summaries` (kroki, sen), `blood_pressure_readings`, `ecg_recordings`, `cycle_days`.
Kolumny profilu w istniejącej tabeli `users` backend dokłada sam przy starcie (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`).
Tabela `health_profiles` z poprzedniej wersji jest nieużywana: `DROP TABLE health_profiles;`.

## Sprawdzenie w bazie

```bash
sudo docker compose exec db psql -U app -d app -c "select metric, count(*), round(avg(value)::numeric,1) from vital_samples group by metric"
sudo docker compose exec db psql -U app -d app -c "select id, email, sex, birth_date, weight_kg, height_cm from users"
```
