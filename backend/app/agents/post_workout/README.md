# PostWorkoutAgent

Agent zbiera krótki wywiad **po każdym treningu**, zapisuje potwierdzone odpowiedzi
w PostgreSQL i tworzy raporty dla zalogowanego użytkownika. Pytania, komentarze i komunikaty API są po angielsku.

## Integracja z aplikacją i bazą

Wykorzystujemy istniejące JWT, `CurrentUser`, sesję SQLAlchemy i tabele:

- `users`: preferencje `post_workout_reporting_frequency` i `timezone`;
- `messages`: historia rozmów, `agent = "post_workout"`, dodatkowe nullable `post_workout_checkin_id`;
- `training_questionnaires`: wybrane odpowiedzi zakończonego wywiadu treningowego jako kontekst komentarza.

Dodajemy dwie tabele:

| Tabela | Co przechowuje |
|---|---|
| `post_workout_checkins` | Jeden wywiad: robocze odpowiedzi, stan, wersja, metadane treningu, potwierdzone oceny, komunikaty bezpieczeństwa i komentarz. |
| `post_workout_reports` | Zapisane obliczenia okresowe, zakres dat, strefa czasowa, wersja algorytmu i komentarz. |

Każdy rekord należy do `users.id`. Endpointy filtrują po użytkowniku z JWT.
Klucz obcy w `messages` sprawdza także zgodność właściciela wiadomości i wywiadu.
Oceny samopoczucia nie trafiają do `vital_samples`, `daily_summaries` ani pozostałych tabel pomiarów zdrowotnych.

Nie ma osobnej tabeli zakończonych treningów. Frontend przekazuje opcjonalne metadane treningu;
`requestId` rozpoczęcia należy wygenerować raz dla tego treningu i zachować do ponowień.
Agent nie korzysta z Chroma ani RAG.

## Uruchomienie

Ustawienia Azure są wspólne z pozostałymi agentami tekstowymi:
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`,
`AZURE_OPENAI_CHAT_DEPLOYMENT`. Deployment musi obsługiwać Structured Outputs.
Nie dodajemy nowego deploymentu ani danych do seedowania.

Z katalogu głównego repozytorium:

```bash
docker compose up -d --build --force-recreate backend
docker compose logs --tail=100 backend
```

Backend podczas startu wykonuje `app.db.migrate.initialize_database()`:
zakłada brakujące tabele i dodaje kolumny oraz ograniczenia do istniejących tabel Postgresa.
Migracja jest transakcyjna, może być uruchamiana wielokrotnie i nie usuwa dotychczasowych danych.
Obejmuje także starsze kolumny profilu użytkownika, których może brakować w lokalnej bazie.

Opcjonalnie po zbudowaniu obrazu można uruchomić ten sam krok ręcznie:

```bash
docker compose run --rm --no-deps backend python -m app.db.migrate
```

Obecny `docker-compose.yml` wystawia backend na porcie **8000**; Swagger: `http://localhost:8000/docs`.
Jeśli zmienisz mapowanie portów, użyj własnego portu w adresach poniżej.
Nie trzeba przebudowywać Postgresa ani ponownie importować embeddingów.

## Uwierzytelnianie i preferencje

Każde żądanie do tego agenta wymaga:

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

Token uzyskasz przez istniejące `POST /api/v1/auth/login` (formularz `username`, `password`).

Preferencje konta ustawiamy przez istniejące `PATCH /api/v1/users/me`:

```json
{
  "post_workout_reporting_frequency": "weekly",
  "timezone": "Europe/Warsaw"
}
```

Dozwolone częstotliwości: `daily`, `weekly`, `monthly`. Strefa musi być prawidłową nazwą IANA.
Domyślnie: `weekly`, `Europe/Warsaw`. Częstotliwość określa **okres raportu**;
wywiad pozostaje po każdym treningu. Nie ma obecnie harmonogramu wysyłania powiadomień ani raportów w tle.

API użytkowników zachowuje dotychczasowy `snake_case`. API nowego agenta zwraca `camelCase`.

## Endpointy

Prefix: `/api/v1/agents/post-workout`.

| Metoda | Ścieżka | Zastosowanie |
|---|---|---|
| POST | `/sessions` | Rozpocznij wywiad; zwraca pierwsze pytanie. |
| GET | `/sessions/{sessionId}` | Pobierz aktualny stan, także po odświeżeniu strony. |
| POST | `/sessions/{sessionId}/chat` | Odpowiedź, pominięcie, korekta, potwierdzenie lub ponowienie komentarza. |
| GET | `/sessions/{sessionId}/history` | Historia wiadomości tej sesji. |
| GET | `/feedback` | Potwierdzone wywiady użytkownika, od najnowszego treningu. |
| POST | `/reports` | Oblicz/zwróć raport i spróbuj wygenerować komentarz. |
| GET | `/reports` | Lista zapisanych raportów użytkownika, od najnowszego obliczenia. |

Listy przyjmują `limit` (1–100, domyślnie 50) i `offset` (domyślnie 0).
Historia jest uporządkowana od najstarszej wiadomości.
`GET /reports` obsługuje także `period`, `start`, `end`; zakres dat filtruje raporty nachodzące na ten zakres.

## Przebieg wywiadu dla frontendu

1. Po zakończeniu treningu wywołaj `/sessions` i zachowaj `sessionId`.
2. Wyświetl `reply` oraz kontrolkę odpowiednią dla `question.type`.
3. Po każdej odpowiedzi zapisz otrzymany stan, szczególnie `version`.
4. Przy `awaiting_confirmation` pokaż `draftFeedback`, przycisk potwierdzenia i możliwość korekty.
5. Po `confirm` pokaż `postWorkoutFeedback`, komentarz oraz ewentualny `notice`.
6. Raport dostępny jest przez `reportId` i listę `/reports`.

### Rozpoczęcie

```http
POST /api/v1/agents/post-workout/sessions
```

```json
{
  "requestId": "1d4cffc2-929d-440a-bd69-734be095c191",
  "workoutEndedAt": "2026-10-01T17:30:00Z",
  "workoutType": "strength",
  "workoutDurationMinutes": 45
}
```

Tylko `requestId` jest wymagany. Gdy pomijasz `workoutEndedAt`, backend przyjmuje moment rozpoczęcia wywiadu.
Data musi zawierać strefę czasową. Czas trwania: 1–600 minut. Typ treningu: maksymalnie 80 znaków.

Początek odpowiedzi (pozostałe pola opisano poniżej):

```json
{
  "sessionId": "e29febdd-e8a9-43e9-807d-1c9d090fd632",
  "version": 0,
  "status": "in_progress",
  "step": 0,
  "total": 6,
  "reply": "Did you feel any pain during your workout, or do you feel pain now?",
  "question": {
    "key": "painExperienced",
    "text": "Did you feel any pain during your workout, or do you feel pain now?",
    "type": "choice",
    "options": [{"value": "yes", "label": "Yes"}, {"value": "no", "label": "No"}],
    "minValue": null,
    "maxValue": null,
    "skippable": true
  }
}
```

Pytania: ból, zmęczenie, samopoczucie względem początku treningu, nastrój,
motywacja do kolejnego treningu, subiektywny wysiłek. Przy bólu dochodzą lokalizacja i intensywność;
`total` zmienia się wtedy z 6 na 8. Wszystkie pytania można pominąć.
Skale to liczby całkowite 0–10, a odpowiedź o zmianie samopoczucia to `better`, `same`, `worse`.
Frontend powinien czytać pytania z odpowiedzi API i nie zakładać stałej kolejności lub liczby kroków.

### Odpowiedzi i pozostałe akcje

```http
POST /api/v1/agents/post-workout/sessions/{sessionId}/chat
```

```json
{
  "requestId": "c095ab47-8a5f-4b49-aa45-aee1b4ed413f",
  "expectedVersion": 0,
  "action": "answer",
  "message": "no"
}
```

Każda nowa akcja wymaga nowego UUID `requestId` oraz ostatniej `version` jako `expectedVersion`.
`action` domyślnie wynosi `answer`. Wysyłaj wartość opcji, np. `no`, albo liczbę jako tekst, np. `"4"`.
Można używać naturalnego języka; wtedy Azure interpretuje odpowiedź na aktualne pytanie.
Backend nie przypisuje liczby do niejednoznacznego „bardzo zmęczona” – prosi o konkretną ocenę.

| Akcja | Dodatkowe pola | Efekt |
|---|---|---|
| `answer` | `message` | Odpowiedź na bieżące pytanie. |
| `skip` | brak | Zapisuje brak odpowiedzi (`null`) i przechodzi dalej. |
| `correct` | `fieldKey`, `message` | Zmienia wcześniej udzieloną odpowiedź przed potwierdzeniem. |
| `confirm` | brak | Zapisuje końcowy wywiad i raport, następnie generuje komentarz. |
| `retry_support` | brak | Ponawia brakujący komentarz ukończonego wywiadu. |

Przykład korekty:

```json
{
  "requestId": "f59a5983-fb7a-4a77-bc6b-813e0e9de573",
  "expectedVersion": 6,
  "action": "correct",
  "fieldKey": "fatigueLevel",
  "message": "3"
}
```

`fieldKey` to klucz pytania, np. `painExperienced`, `painLocations`, `painIntensity`,
`fatigueLevel`, `feelingChange`, `moodLevel`, `motivationLevel`, `perceivedExertionRating`.
Zmiana `painExperienced` na `no` usuwa szczegóły bólu z roboczych odpowiedzi.

### Pola odpowiedzi i stany

| Pole | Znaczenie |
|---|---|
| `sessionId`, `version` | Identyfikator i wersja wywiadu. |
| `status` | `in_progress`, `awaiting_confirmation`, `completed` lub `interrupted`. |
| `step`, `total` | Liczba odpowiedzianych/pominiętych aktywnych pytań i liczba wszystkich aktywnych pytań. |
| `reply` | Tekst do pokazania w rozmowie. |
| `question` | Pytanie do kolejnego kroku; `null` podczas potwierdzenia, po zakończeniu lub przerwaniu. |
| `draftFeedback` | Robocze odpowiedzi, dostępne także przed końcem wywiadu. |
| `postWorkoutFeedback` | Potwierdzone dane; wcześniej `null`. |
| `notice` | Komunikat bezpieczeństwa lub `null`. Wyświetl go oddzielnie od komentarza LLM. |
| `support` | Komentarz: `pending`, `available`, `unavailable`; przed potwierdzeniem `null`. |
| `reportId` | Identyfikator zapisanego raportu po potwierdzeniu. |

Przykład `postWorkoutFeedback`:

```json
{
  "workoutEndedAt": "2026-10-01T17:30:00Z",
  "workoutType": "strength",
  "workoutDurationMinutes": 45,
  "fatigueLevel": 4,
  "feelingChange": "better",
  "moodLevel": 7,
  "motivationLevel": 8,
  "perceivedExertionRating": 7,
  "pain": {"experienced": false, "intensity": 0, "locations": [], "description": null}
}
```

Nie utożsamiaj `null` z zerem. Pominięty ból ma `experienced: null`, `intensity: null`.
Jawne „nie boli” ma `experienced: false`, `intensity: 0`.
Po `completed` nie można zmieniać odpowiedzi. Przerwane wywiady nie wchodzą do raportów.

### Ponawianie i równoległe żądania

Przy błędzie sieci ponów **ten sam payload z tym samym `requestId`**, także z pierwotnym `expectedVersion`.
Backend zwróci zapisany wynik tej akcji, bez dodawania kolejnej odpowiedzi.
Ponowienie `/sessions` zwraca aktualny stan tej samej sesji.
Ten sam UUID z innym payloadem powoduje HTTP 409.

Przy konflikcie wersji pobierz `GET /sessions/{sessionId}`, odśwież ekran i wyślij nową akcję z nowym UUID.
Nie zwiększaj wersji samodzielnie. Dwie karty przeglądarki nie mogą nadpisać swoich odpowiedzi.

Jeśli odpowiedź na potwierdzenie została przerwana przez timeout, pobierz stan sesji.
`pending` oznacza, że potwierdzone dane są już zapisane. Powtórzenie pierwotnego `confirm`
nie uruchamia drugiego wywołania Azure. Gdy komentarz jest `unavailable`, użyj `retry_support`.
Porzucone `pending` można ponowić po dwóch minutach. W tym czasie pobieraj stan bez tworzenia nowych akcji.

## Raporty i trendy

Raport dla domyślnego okresu powstaje przy potwierdzeniu wywiadu.
Raport można też obliczyć na żądanie:

```http
POST /api/v1/agents/post-workout/reports
```

```json
{"period": "weekly", "anchorDate": "2026-10-01", "regenerateComment": false}
```

Wszystkie pola są opcjonalne, ale wyślij przynajmniej `{}` jako body.
Domyślny okres pochodzi z konta, a data to dzisiaj w strefie użytkownika.
`anchorDate` wskazuje dzień należący do wybranego okresu; nie może być w przyszłości.
`regenerateComment: true` odświeża komentarz, zachowując obliczenia tego samego zestawu danych.

- Dzień: lokalna doba; tydzień: poniedziałek–niedziela; miesiąc: kalendarzowy.
- Daty `periodStart` i `periodEnd` są włączne. Przypisanie wywiadu do okresu używa `workoutEndedAt`.
- `isPartial: true` oznacza, że okres jeszcze trwa. Porównanie używa poprzedniego pełnego okresu;
  pokazuj daty, liczebności i oznaczenie niepełnego okresu.
- Python liczy mediany, liczby odpowiedzi i różnicę median. Model nie oblicza statystyk.
- Dla każdej skali porównanie wymaga co najmniej trzech niepustych odpowiedzi w każdym okresie.
  To reguła produktu, nie próg medyczny ani test istotności statystycznej.
- Przy mniejszej liczbie odpowiedzi: `status: "insufficient_data"`, `delta: null`;
  mediany i liczebności pozostają dostępne. Globalne `ok` oznacza, że porównywalna jest przynajmniej jedna skala.
- Dni bez wywiadu nie są dopisywane jako zera. Odpowiedzi `better/same/worse` i ból są zliczane osobno.
- `observations` zawiera opisowe fakty obliczone przez backend. `support.observations`
  zawiera wybrane spośród nich teksty; komentarz LLM nie dodaje liczb ani nowych identyfikatorów faktów.

Raporty są zapisanymi wersjami obliczeń. Kolejny wywiad w tym samym okresie tworzy nowy snapshot;
lista może zawierać kilka raportów dla tego samego zakresu dat. Dla karty „aktualny raport” użyj
`POST /reports` albo najnowszego pasującego raportu z listy.
Zmiana preferencji konta nie przepisuje historycznych raportów.

## Azure i błędy

Azure zwraca Structured Outputs z `strict: true`; SDK parsuje wynik do Pydantic.
Backend dodatkowo sprawdza typy, zakres 0–10, dozwolone wartości i identyfikatory obserwacji.
Jawne liczby i wybory obsługuje bez LLM. Naturalny język oraz spersonalizowany komentarz używają prawdziwego Azure.
Brak credentiali nie uruchamia atrapy.

| HTTP | Znaczenie |
|---|---|
| 200 | Zapis/odczyt się udał. Sprawdź też `status`, `notice` i `support.status`. |
| 401 | Brak lub nieprawidłowy JWT. |
| 404 | Sesja nie istnieje lub należy do innego użytkownika. |
| 409 | Konflikt wersji, ponowne użycie UUID z inną treścią albo akcja niedozwolona w tym stanie. |
| 422 | Nieprawidłowy body, zakres dat, metadane lub `fieldKey`. |
| 502 | Awaria Azure lub niepoprawny wynik podczas interpretacji odpowiedzi; stan nie przesuwa się dalej. |
| 503 | Brak konfiguracji Azure podczas interpretacji tekstu. |

Błędna lub niejednoznaczna ocena w treści wiadomości zwraca HTTP 200 z ponowionym pytaniem.
**Awaria Azure podczas komentarza końcowego zwraca HTTP 200 z `support.status: "unavailable"`.**
Potwierdzony wywiad i obliczenia raportu są już zapisane. Frontend powinien pokazać dane i możliwość ponowienia komentarza.

## Komunikaty bezpieczeństwa

Backend sprawdza literalne opisy objawów oraz weryfikuje cytaty zgłoszone przez model.
Zgłoszenie pilnych objawów albo ryzyka samouszkodzenia przerywa wywiad (`interrupted`)
i daje stały komunikat o pilnym kontakcie z człowiekiem/pomocą medyczną.
Wysoka deklarowana intensywność bólu (7–10), pogarszający się ból lub ograniczenie ruchu
mogą dać `notice.level: "consultation"`. Utrzymujący się zgłoszony dystres może sugerować
kontakt z lekarzem, psychologiem lub psychoterapeutą. Pojedyncza niska ocena nastroju nie uruchamia takiej sugestii.
Próg bólu jest regułą produktu; nie stanowi rozpoznania ani oceny, że pozostałe wartości są bezpieczne.

Frontend przy `urgent` pokazuje `notice.message` i nie kontynuuje kwestionariusza.
Przy `consultation` pokazuje komunikat także wtedy, gdy komentarz Azure jest niedostępny.
Rozpoznawanie tekstu ma ograniczenia językowe; brak komunikatu nie jest potwierdzeniem bezpieczeństwa.
Agent nie diagnozuje i nie zastępuje konsultacji.

Źródła wspierające treść komunikatów: [NHS – chest pain](https://www.nhs.uk/symptoms/chest-pain/),
[NHS – sprains and strains](https://www.nhs.uk/conditions/sprains-and-strains/),
[NHS – low mood](https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/feelings-and-symptoms/low-mood-sadness-depression/).

## Pliki implementacji

- `questionnaire.py`: pytania, aktywne kroki i jawne odpowiedzi bez LLM.
- `agent.py`: przebieg wywiadu, potwierdzenie i ponawianie komentarza.
- `prompts.py`, `llm.py`: angielskie prompty i klient Structured Outputs Azure.
- `safety.py`: komunikaty i weryfikacja zgłoszonych objawów.
- `app/api/v1/router_post_workout.py`: endpointy i JWT.
- `app/models/post_workout.py`, `app/schemas/post_workout.py`: modele bazy i kontrakty API.
- `app/services/post_workout.py`, `post_workout_reports.py`: zapis, idempotencja i raporty.
- `app/statistics/post_workout.py`: obliczenia opisowe i granice okresów.
- `app/db/migrate.py`: aktualizacja schematu bazy przy starcie lub ręcznie.

Testy w `tests/test_post_workout.py` i `tests/test_post_workout_trends.py` używają izolowanej bazy
oraz podstawionych odpowiedzi Azure. Test klienta SDK sprawdza wysyłany schemat i rzeczywisty parser bez połączenia z Azure.
