# Dane RAG dla VisionAgenta

Ten folder zawiera karty maszyn przeznaczone do osobnej kolekcji wiedzy VisionAgenta.

## Obecna zawartość

`machines.example.json` to przykład struktury danych z polami do uzupełnienia. Każdy obiekt w tablicy reprezentuje jedną maszynę. Wartości są demonstracyjne i służą do zaplanowania schematu oraz testów.

## Dodawanie docelowych danych

Po opracowaniu materiałów utwórz w tym folderze `machines.json`, korzystając ze struktury przykładu. Uzupełnij angielską nazwę w polu `name`, aliasy, mięśnie, instrukcje i źródła. Nadaj każdej karcie unikalny, stały `machine_id`, np. `chest_press`.

Pola karty:

| Pole | Typ | Znaczenie |
|---|---|---|
| `machine_id` | string | Stały identyfikator maszyny |
| `name` | string | Jedna angielska nazwa maszyny, używana przy rozpoznawaniu i zwracana jako `machine_name` |
| `aliases` | array[string] | Alternatywne nazwy |
| `category` | string | Kategoria urządzenia |
| `primary_muscles` | array[string] | Główne partie mięśniowe |
| `secondary_muscles` | array[string] | Pomocnicze partie mięśniowe |
| `description` | string | Opis zastosowania |
| `setup_steps` | array[string] | Kroki przygotowania urządzenia |
| `exercise_steps` | array[string] | Kroki wykonania ćwiczenia |
| `tips` | array[string] | Wskazówki i częste błędy |
| `sources` | array[string] | Źródła informacji, np. tytuł instrukcji i URL |

## Import do Chromy

Importer sprawdza schemat kart i unikalność identyfikatorów, tworzy embeddingi Azure oraz zapisuje dane do osobnej kolekcji `gym_machines_<embedding_tag>`. Ponowny import aktualizuje karty po `machine_id`; nie usuwa kart pominiętych w nowym pliku.

Polecenia uruchamiaj z folderu backendu:

```bash
# Sprawdzenie przykładu bez credentiali i bez połączenia z Chroma
uv run python -m app.agents.vision.seed --file docs_RAG/vision/machines.example.json --dry-run

# Sprawdzenie docelowego pliku machines.json
uv run python -m app.agents.vision.seed --dry-run

# Import docelowych danych do Chromy
uv run python -m app.agents.vision.seed
```

Domyślny plik to `docs_RAG/vision/machines.json`. Przykład można wczytać wyłącznie przez jawne wskazanie `--file`; nie jest importowany automatycznie. `--dry-run` tylko waliduje dane i nie łączy się z usługami.

Samo dodanie lub zmiana pliku nie aktualizuje Chromy — ponownie uruchom importer. Obecny importer treningowy odczytuje pliki PDF/TXT bezpośrednio w `docs_RAG` i pomija ten podfolder.

Endpoint `POST /api/v1/agents/vision/analyze` rozpoznaje maszynę z katalogu w Chroma i generuje opis z jej karty. Dodaj opracowane dane do `machines.json` przed użyciem ze zdjęciami rzeczywistych urządzeń.

