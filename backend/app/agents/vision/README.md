# Vision Agent — integracja z frontendem

Użytkownik wybiera zdjęcie maszyny z siłowni. Frontend wysyła plik do backendu, a w odpowiedzi otrzymuje rozpoznaną maszynę oraz prosty opis jej użycia: trenowane mięśnie, przygotowanie, kroki ćwiczenia i wskazówki.

Model tekstowy ma generować treść **po angielsku**, prostymi słowami dla początkującego użytkownika. Nazwa, kategoria, źródła oraz identyfikatory mięśni pochodzą z karty maszyny w bazie wiedzy. Model nie wybiera ani nie zmienia obszarów mapy.

## Endpoint i adres backendu

```text
POST /api/v1/agents/vision/analyze
```

| Ustawienie | Wartość |
|---|---|
| Backend w obecnym Docker Compose | `http://localhost:8002` |
| Pełny lokalny adres endpointu | `http://localhost:8002/api/v1/agents/vision/analyze` |
| Swagger | `http://localhost:8002/docs` |
| Metoda | `POST` |
| Treść żądania | `multipart/form-data` |
| Odpowiedź sukcesu | `200 OK`, `application/json` |
| Logowanie | Niewymagane; endpoint nie wymaga tokenu JWT |

Adres backendu trzymaj w konfiguracji frontendu. Przy uruchomieniu backendu poza Dockerem port może być inny, np. `8000`. Port `8001` w Compose należy do Chromy — frontend wywołuje backend.

To jedno żądanie: backend rozpoznaje maszynę, pobiera jej kartę i generuje opis, następnie zwraca cały wynik. Endpoint nie wysyła częściowych wyników, nie streamuje tekstu i nie zwraca identyfikatora zadania do odpytywania.

## Wysyłanie zdjęcia

Wymagane jest jedno pole formularza:

| Pole | Typ | Znaczenie |
|---|---|---|
| `file` | Plik binarny | Zdjęcie maszyny; plik nie może być pusty |

Wyślij obiekt `File` przez `FormData`. Endpoint nie przyjmuje zdjęcia jako JSON, ciągu base64 ani adresu URL. Nie trzeba wysyłać nazwy maszyny, identyfikatora użytkownika ani dodatkowego promptu.

**Nie ustawiaj ręcznie nagłówka `Content-Type` przy użyciu `fetch` z `FormData`.** Przeglądarka doda `multipart/form-data` wraz z prawidłowym `boundary`.

Obsługiwane formaty: **JPG/JPEG, PNG, WEBP, HEIC/HEIF, AVIF, BMP, TIFF/TIF i GIF**.
Frontend wysyła oryginalny plik; nie musi sam konwertować zdjęć z iPhone'a.

```html
<input
  type="file"
  accept=".jpg,.jpeg,.png,.webp,.heic,.heif,.avif,.bmp,.tif,.tiff,.gif,image/jpeg,image/png,image/webp,image/heic,image/heif,image/avif,image/bmp,image/tiff,image/gif"
/>
```

`accept` jest podpowiedzią dla selektora. Backend rozpoznaje format z zawartości pliku,
nie z rozszerzenia ani deklarowanego MIME. Nieobsługiwany lub uszkodzony obraz zwraca `422`.

Przed analizą backend przygotowuje jeden JPEG:

- poprawia orientację ze zdjęcia;
- wybiera pierwszą klatkę GIF, WebP lub AVIF, pierwszą stronę TIFF albo główne zdjęcie HEIF;
- zamienia przezroczystość na białe tło i kolory na RGB;
- zmniejsza obraz do maksymalnie **2048 px na dłuższym boku**, zachowując proporcje;
- nie kopiuje metadanych EXIF i profilu ICC do wyjściowego JPEG.

Limit wejściowego pliku określa `MAX_UPLOAD_MB` w konfiguracji backendu: domyślnie **10 MB**
(10 × 1024 × 1024 bajtów). Maksymalna rozdzielczość przed konwersją to **60 megapikseli**.
Przekroczenie limitu pliku lub rozdzielczości zwraca `413` i nie uruchamia analizy obrazu przez model.
Nie gwarantujemy odczytu uszkodzonych plików ani dowolnych wariantów kodeków w tych kontenerach.

Odczyt i konwersja używają [Pillow](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)
oraz [pillow-heif](https://pillow-heif.readthedocs.io/en/stable/pillow-plugin.html).
Nie wymagają nowego deploymentu Azure, zmiany promptów ani importowania embeddingów.

## Odpowiedź sukcesu

Przykład struktury odpowiedzi; treść i liczba elementów list zależą od karty maszyny oraz wygenerowanego opisu:

```json
{
  "description": "This machine helps you train your legs. You push the platform away with your feet.",
  "primary_muscles": ["quads", "glutes"],
  "secondary_muscles": ["hamstrings", "calves", "adductors"],
  "setup_steps": [
    "Sit on the seat.",
    "Rest your back against the backrest.",
    "Place your feet on the platform."
  ],
  "exercise_steps": [
    "Push the platform away with your feet.",
    "Slowly bring the platform back towards you."
  ],
  "tips": ["Keep your back against the backrest."],
  "machine_id": "leg_press_45",
  "machine_name": "45-Degree Leg Press Machine",
  "category": "Lower Body Strength",
  "sources": ["General Kinesiology Guidelines", "Standard Gym Equipment Manuals"]
}
```

| Pole | Typ | Znaczenie / sugerowane wyświetlenie |
|---|---|---|
| `machine_id` | `string` | Stały identyfikator karty maszyny, np. do logiki frontendu |
| `machine_name` | `string` | Angielska nazwa urządzenia; tytuł widoku |
| `category` | `string` | Kategoria z karty; etykieta pod tytułem |
| `description` | `string` | Krótki opis zastosowania prostymi słowami |
| `primary_muscles` | `RegionId[]` | Główne obszary mapy, skopiowane z karty |
| `secondary_muscles` | `RegionId[]` | Pomocnicze obszary mapy, skopiowane z karty |
| `setup_steps` | `string[]` | Przygotowanie do ćwiczenia; lista numerowana |
| `exercise_steps` | `string[]` | Kolejne kroki ćwiczenia; lista numerowana |
| `tips` | `string[]` | Dodatkowe wskazówki |
| `sources` | `string[]` | Źródła zapisane w karcie maszyny |

Wszystkie pola są obecne w odpowiedzi sukcesu. Obie listy mięśni oraz `tips` mogą być pustymi tablicami. Puste mięśnie oznaczają brak precyzyjnego przypisania do mapy, np. dla samej ławki lub sprzętu zależnego od wybranego ćwiczenia. `description` jest niepuste; `setup_steps` i `exercise_steps` zawierają przynajmniej jeden niepusty element.

`machine_id` identyfikuje typ maszyny w katalogu, a nie konkretny egzemplarz czy numer produktu producenta. Odpowiedź nie zawiera oceny pewności rozpoznania, URL zdjęcia ani osobnego pola `message`.

`sources` to teksty z karty, niekoniecznie adresy URL. Wyświetlaj je jako tekst; link twórz tylko wtedy, gdy wpis jest prawidłowym adresem. Pola odpowiedzi są zwykłym tekstem, więc nie wymagają renderowania HTML ani Markdown. Zachowaj kolejność kroków i nie zakładaj stałej długości list.

## Stałe identyfikatory dla mapy mięśni

`primary_muscles` i `secondary_muscles` zawierają wyłącznie wartości `RegionId` z
`frontend/src/features/muscles/muscleRegions.ts`. Wielkość liter i myślniki są częścią kontraktu:

```text
chest, shoulders, rear-deltoids, biceps, triceps, forearms, abs, obliques,
traps, lats, lower-back, glutes, quads, hamstrings, calves, adductors
```

Backend waliduje każdą kartę i odpowiedź. Nazwę do wyświetlania pobieraj z `REGION_LABELS`,
np. `REGION_LABELS["quads"]`. Nie wyświetlaj identyfikatorów jako wygenerowanych zdań.
Tekstowy model zwraca tylko opis, przygotowanie, kroki i wskazówki; backend dokłada listy
mięśni z karty bez ich tłumaczenia. Zestaw pól publicznego JSON-a pozostaje taki sam.

### Dostosowanie obecnego `regionsFor()` na froncie

Kod frontendu znajduje się w innym checkoutcie/branchu; poniższą zmianę należy zastosować tam.
Najpierw obsłuż identyfikator bezpośrednio, a dopiero potem starsze etykiety przez `RULES`.
To istotne dla `rear-deltoids`, `lower-back` i `shoulders`: reguły szukające spacji lub
ogólnych słów mogą pominąć identyfikator albo zaznaczyć dodatkowy obszar.

```typescript
function isRegionId(value: string): value is RegionId {
  return Object.prototype.hasOwnProperty.call(REGION_LABELS, value);
}

export function regionsFor(labels: string[]): Set<RegionId> {
  const found = new Set<RegionId>();
  for (const label of labels) {
    const lower = label.toLowerCase();
    if (isRegionId(lower)) {
      found.add(lower);
      continue;
    }
    // Zachowaj dotychczasowe reguły jako obsługę starszych odpowiedzi.
    for (const rule of RULES) {
      if (rule.test(lower)) {
        rule.regions.forEach((region) => found.add(region));
        break;
      }
    }
  }
  return found;
}
```

Lista oznacza obszary rysunku, nie pełny atlas anatomiczny. `shoulders` oznacza przód
barków, a `rear-deltoids` ich tył. Nie przypisujemy automatycznie ogólnego `Back` do
`lats`, `Core` do `abs` ani `Full Body` do wszystkich obszarów. Nieobsługiwane i warunkowe
informacje pozostają w wewnętrznym `muscle_notes` karty, jako kontekst dla opisu.
`muscle_notes` nie jest polem odpowiedzi endpointu.

## Przykład TypeScript: typy i wywołanie

Przykład działa niezależnie od frameworka. `apiBaseUrl` oznacza sam adres backendu, np. `http://localhost:8002`, bez `/api/v1` na końcu.

```typescript
// W aplikacji użyj istniejącego RegionId z muscleRegions.ts.
export type RegionId =
  | "chest" | "shoulders" | "rear-deltoids" | "biceps" | "triceps" | "forearms"
  | "abs" | "obliques" | "traps" | "lats" | "lower-back" | "glutes"
  | "quads" | "hamstrings" | "calves" | "adductors";

export interface VisionResponse {
  machine_id: string;
  machine_name: string;
  category: string;
  description: string;
  primary_muscles: RegionId[];
  secondary_muscles: RegionId[];
  setup_steps: string[];
  exercise_steps: string[];
  tips: string[];
  sources: string[];
}

export class VisionApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "VisionApiError";
  }
}

function getErrorMessage(body: unknown, status: number): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = body.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item: unknown) => {
        if (
          typeof item === "object" && item !== null &&
          "msg" in item && typeof item.msg === "string"
        ) return [item.msg];
        return [];
      });
      if (messages.length) return messages.join("; ");
    }
  }
  return `Image analysis failed (HTTP ${status}).`;
}

export async function analyzeMachine(
  file: File,
  apiBaseUrl: string,
  signal?: AbortSignal,
): Promise<VisionResponse> {
  const form = new FormData();
  form.append("file", file, file.name);

  const response = await fetch(
    `${apiBaseUrl.replace(/\/+$/, "")}/api/v1/agents/vision/analyze`,
    {
      method: "POST",
      headers: { Accept: "application/json" },
      body: form,
      signal,
    },
  );
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    throw new VisionApiError(response.status, getErrorMessage(body, response.status));
  }
  if (typeof body !== "object" || body === null || Array.isArray(body)) {
    throw new Error("The backend returned an invalid JSON response.");
  }
  return body as VisionResponse;
}
```

Backend waliduje odpowiedź według [schematu Pydantic](../../schemas/vision.py). Interfejs TypeScript i `as VisionResponse` opisują typ dla kompilatora; sam przykład nie sprawdza każdego pola odpowiedzi w przeglądarce.

W obsłudze wyboru pliku lub przycisku:

```typescript
// file: File otrzymany z input.files[0]
try {
  const result = await analyzeMachine(file, "http://localhost:8002");
  // Zapisz result w stanie aplikacji i wyświetl sekcje odpowiedzi.
  console.log(result.machine_name, result.description);
} catch (error) {
  if (error instanceof VisionApiError) {
    console.error(error.status, error.message);
    // Wybierz komunikat dla użytkownika na podstawie statusu HTTP.
  } else {
    console.error(error);
    // Obsłuż m.in. brak połączenia, błąd CORS lub nieprawidłową odpowiedź.
  }
}
```

Na czas oczekiwania pokaż stan ładowania i zablokuj ponowne wysłanie tego samego formularza. Widok wyniku wyświetl po odebraniu całej odpowiedzi. Opcjonalny `AbortSignal` pozwala przerwać oczekiwanie po stronie klienta; nie gwarantuje przerwania rozpoczętych wywołań Azure na backendzie.

## Błędy

| Status | Kiedy występuje | Reakcja frontendu |
|---|---|---|
| `422` | Brak pola `file`, pusty, uszkodzony lub nieobsługiwany obraz, zdjęcie bez sprzętu siłownianego, niepewne rozpoznanie (`confidence` inne niż `high`) albo maszyna spoza obsługiwanego katalogu | Poproś o wybór zdjęcia; przy braku rozpoznania pokaż `detail`, który mówi, co poprawić |
| `413` | Plik przekracza `MAX_UPLOAD_MB` lub obraz ma ponad 60 megapikseli | Poproś o mniejsze zdjęcie lub niższą rozdzielczość |
| `502` | Błąd dostawcy modelu albo odpowiedź modelu odrzucona, ucięta lub niezgodna ze schematem | Pokaż błąd analizy i możliwość ponowienia |
| `503` | Brak konfiguracji Azure, pusty katalog, brak karty lub stare/nieprawidłowe karty w Chroma wymagające ponownego importu | Pokaż komunikat o niedostępności analizy; konfigurację poprawia backend |
| Inny błąd, np. `500` | Nieobsłużony błąd serwera, np. problem połączenia z Chroma | Pokaż ogólny komunikat o błędzie usługi |

Komunikaty błędów rozpoznania (`detail`):

- `"This photo doesn't show gym equipment. Take a photo of the machine you want to use."`: na zdjęciu nie ma sprzętu.
- `"I'm not sure which machine this is. Take a clearer photo of the whole machine."`: model nie jest pewny dopasowania.
- `"The image does not match a machine in the supported catalog"`: sprzęt spoza katalogu.

Błędy walidacji FastAPI, np. brak pola `file`, zwracają `detail` jako tablicę obiektów zawierających m.in. `loc`, `msg` i `type`. Pozostałe opisane błędy zwykle zwracają `detail` jako tekst. Nie zakładaj jednego typu tego pola ani identycznego komunikatu dla każdego `422`.

Sprawdzaj `response.ok`: `fetch` nie rzuca wyjątku automatycznie dla statusów `413`, `422`, `502` czy `503`. Błąd sieci lub CORS może odrzucić `fetch` bez odpowiedzi HTTP dostępnej dla aplikacji.

## CORS i konfiguracja frontendu

Domyślne dozwolone adresy frontendu to `http://localhost:3000` oraz `http://localhost:5173`. Przy innym adresie ustaw `CORS_ORIGINS` w konfiguracji backendu, np.:

```dotenv
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
```

`localhost` i `127.0.0.1` to różne originy. Liczą się również protokół i port. Po zmianie konfiguracji kontenera odtwórz backend. Ten endpoint nie wymaga ustawienia `credentials: "include"`.

Frontend potrzebuje wyłącznie adresu backendu. Klucz Azure, nazwy deploymentów i połączenie z Chroma są konfiguracją backendu; nie umieszczaj ich w kodzie ani zmiennych udostępnianych przeglądarce.

## Test ręczny w Swaggerze lub terminalu

W Swaggerze otwórz **vision agent → POST /api/v1/agents/vision/analyze**, wybierz **Try it out**, wskaż plik i kliknij **Execute**. Nie trzeba używać **Authorize**.

Przykład dla Bash/WSL, z katalogu zawierającego zdjęcie:

```bash
curl -X POST 'http://localhost:8002/api/v1/agents/vision/analyze' \
  -H 'Accept: application/json' \
  -F 'file=@leg-press.jpg;type=image/jpeg'
```

Do działania potrzebny jest skonfigurowany Azure oraz katalog maszyn zaimportowany do Chromy. Brak rozpoznania może oznaczać, że urządzenia nie ma w katalogu — agent obsługuje karty dostępne w bazie wiedzy.

## Co robi backend i gdzie szukać kodu

1. [Endpoint](../../api/v1/vision.py) odczytuje zdjęcie z pola `file` z limitem rozmiaru,
   a [przygotowanie obrazu](images.py) dekoduje je i konwertuje do JPEG w osobnym wątku.
2. [Agent](agent.py) pobiera katalog maszyn z osobnej kolekcji Chromy.
3. [Model vision](llm.py) identyfikuje maszynę z tego katalogu.
4. [Warstwa wiedzy](knowledge.py) wyszukuje kartę przez embedding tekstowej nazwy z filtrem po rozpoznanym `machine_id`.
5. Model tekstowy generuje cztery pola: `description`, `setup_steps`, `exercise_steps`, `tips`, zgodnie z [promptem](prompts.py) i schematem Structured Outputs. Backend waliduje ich strukturę, typy i wymagane niepuste wartości.
6. Backend dodaje z karty `primary_muscles`, `secondary_muscles`, `machine_id`, `machine_name`, `category` i `sources`, następnie zwraca jeden obiekt JSON.

Walidacja schematu nie sprawdza poprawności merytorycznej instrukcji ani języka tekstu. Model jest instruowany, aby korzystać z karty i odpowiadać po angielsku.

Zdjęcie nie jest zapisywane przez ten endpoint do historii użytkownika ani jako embedding w Chroma. Jest przesyłane do modelu Azure do analizy. Chroma przechowuje karty maszyn i embeddingi ich tekstu.

Dokumentacja uruchomienia backendu: [backend/README.md](../../../README.md). Przygotowanie i import kart: [docs_RAG/vision/README.md](../../../docs_RAG/vision/README.md).

Komendy poniżej uruchamiaj z głównego folderu repozytorium, zawierającego `docker-compose.yml`:

```bash
# Po zmianach kodu lub promptu backendu
docker compose up -d --build --force-recreate backend

# Po zmianach kart w backend/docs_RAG/vision/machines.json:
# najpierw przebudowa, aby zaktualizować plik w obrazie, potem import
docker compose up -d --build --force-recreate backend
docker compose exec backend python -m app.agents.vision.seed

# Po zmianie samego backend/.env
docker compose up -d --force-recreate backend
```

Zmiana samego promptu nie wymaga ponownego importu embeddingów. Zmiana samego README nie wymaga przebudowy kontenera. Frontend nie wywołuje importera — to czynność po stronie backendu.

### Migracja kart do stałych nazw mięśni

Po wdrożeniu tego kontraktu konieczny jest ponowny import wszystkich kart ze starymi nazwami:

```bash
docker compose up -d --build --force-recreate backend
docker compose exec backend python -m app.agents.vision.seed --dry-run
docker compose exec backend python -m app.agents.vision.seed
```

Do zakończenia importu endpoint może zwracać `503` z komunikatem o nieprawidłowym schemacie kart.
Importer aktualizuje istniejące identyfikatory i nie usuwa kolekcji ani pozostałych danych.
Karty, które były w Chroma, ale nie występują w pliku, pozostają w kolekcji: również trzeba
je zaktualizować i dołączyć do importu, jeżeli mają stare nazwy. Nie usuwaj wolumenów Dockera.
