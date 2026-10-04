# Dane RAG dla VisionAgenta

Ten folder zawiera karty maszyn dla osobnej kolekcji wiedzy VisionAgenta.
`machines.json` zawiera obecnie 37 kart. Każda karta opisuje jeden typ sprzętu.
Przed importem nowych materiałów sprawdź ich treść i źródła.

## Pola karty

| Pole | Typ | Znaczenie |
|---|---|---|
| `machine_id` | string | Unikalny, stały identyfikator maszyny |
| `name` | string | Jedna angielska nazwa; zwracana jako `machine_name` |
| `aliases` | array[string] | Alternatywne nazwy |
| `category` | string | Kategoria urządzenia |
| `primary_muscles` | array[MuscleRegion] | Główne obszary mapy; może być `[]` |
| `secondary_muscles` | array[MuscleRegion] | Pomocnicze obszary mapy; może być `[]` |
| `muscle_notes` | array[string], opcjonalne | Kontekst nieprzypisany do mapy; domyślnie `[]` |
| `description` | string | Niepusty opis zastosowania |
| `setup_steps` | array[string] | Co najmniej jeden krok przygotowania |
| `exercise_steps` | array[string] | Co najmniej jeden krok ćwiczenia |
| `tips` | array[string] | Wskazówki; może być `[]` |
| `sources` | array[string] | Co najmniej jedno źródło |

Nie dodawaj pustych tekstów ani powtórzonych identyfikatorów wewnątrz listy mięśni.

## Słownik mięśni dla mapy

Używaj wyłącznie następujących wartości, identycznych z `RegionId` frontendu:

```text
chest, shoulders, rear-deltoids, biceps, triceps, forearms, abs, obliques,
traps, lats, lower-back, glutes, quads, hamstrings, calves, adductors
```

Przykład pól mięśni w karcie leg press:

```json
{
  "primary_muscles": ["quads", "glutes"],
  "secondary_muscles": ["hamstrings", "calves", "adductors"]
}
```

To fragment karty, nie kompletny dokument do importu. Pozostałe wymagane pola weź z istniejących kart.
Backend kopiuje obie listy bezpośrednio do odpowiedzi endpointu. Model tekstowy nie generuje tych list.

### Zasady przypisania istniejących kart

- Jednoznaczne nazwy są zastąpione identyfikatorem: Quadriceps → `quads`, Latissimus Dorsi →
  `lats`, Anterior Deltoids → `shoulders`, Posterior/Rear Deltoids → `rear-deltoids`,
  Erector Spinae → `lower-back`, Rectus Abdominis → `abs`.
- Obszary mapy grupują niektóre mięśnie: Brachialis → obszar `biceps`, Brachioradialis →
  `forearms`, Gluteus Medius/Minimus → `glutes`, Gastrocnemius/Soleus → `calves`.
  Identyfikator obszaru nie oznacza, że te mięśnie są anatomicznie tym samym mięśniem.
- Ogólne Back, Core, Deltoids i Shoulders pozostają w `muscle_notes`; bez precyzyjnego
  wskazania nie przypisujemy ich do konkretnego obszaru. Dotyczy to również Rhomboids,
  dla których mapa nie ma osobnego regionu.
- Cardiovascular System, Stabilizer Muscles, Full Body, Iliopsoas, Arms (if using moving handles)
  i N/A pozostają w `muscle_notes`. Nie kolorujemy wszystkich mięśni ani przypadkowego obszaru.
- Warunkowe wpisy, np. Glutes (depending on exercise) i Back (if pulling), pozostają tekstem
  z zachowanym warunkiem. Notatki mają prefiks Primary/Secondary zachowujący rolę z oryginalnej karty.
- Sprzęt bez konkretnego przypisania może mieć obie listy puste, np. sama ławka.
  To nie oznacza, że ćwiczenie na tym sprzęcie nie angażuje mięśni.

`muscle_notes` trafia do kontekstu tekstowego modelu, który może uwzględnić je w prostym opisie
lub wskazówkach. Nie jest nowym polem publicznej odpowiedzi. Zachowaj warunki dotyczące konkretnego
ćwiczenia również w opisie i instrukcjach karty. Dla wielofunkcyjnego sprzętu mapa pozostaje
informacją z karty sprzętu, nie rozpoznaniem wykonywanego ćwiczenia.

## Walidacja i import do Chromy

Z folderu `backend`:

```bash
# Walidacja bez credentiali i bez połączenia z Chroma
uv run python -m app.agents.vision.seed --dry-run

# Import zwalidowanych kart; wymaga Azure i Chroma
uv run python -m app.agents.vision.seed

# Własny plik musi spełniać ten sam schemat
uv run python -m app.agents.vision.seed --file docs_RAG/vision/my-machines.json --dry-run
```

Domyślny plik to `docs_RAG/vision/machines.json`. Importer sprawdza schemat, dozwolone identyfikatory
mięśni i unikalność `machine_id`, tworzy embeddingi Azure i zapisuje karty do kolekcji
`gym_machines_<embedding_tag>`. Kolekcja jest oddzielona od historii użytkowników i dokumentów treningowych.

Z głównego folderu repozytorium z `docker-compose.yml`:

```bash
# Obraz musi zawierać aktualny kod i plik kart
docker compose up -d --build --force-recreate backend
docker compose exec backend python -m app.agents.vision.seed --dry-run
docker compose exec backend python -m app.agents.vision.seed
```

Po zmianie nazw mięśni ponowny import jest wymagany. Stare karty w Chroma nie są automatycznie
zgadywane ani mapowane: endpoint zwróci `503` z instrukcją ponownego importu, dopóki katalog nie
spełnia nowego schematu. Ponowny seed nadpisuje karty po `machine_id`, bez duplikatów.
Nie usuwa kart pominiętych w pliku; dodatkowe stare karty również trzeba poprawić i zaimportować.
Nie trzeba usuwać kolekcji ani wolumenów Dockera.

Samo zmienienie pliku nie aktualizuje Chromy. Obecny importer treningowy PDF/TXT pomija ten podfolder.
Dokumentacja endpointu i zmiany `regionsFor()` dla frontendu: [VisionAgent README](../../app/agents/vision/README.md).
