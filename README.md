<div align="center">

# SportPet

**Zmień nastawienie i postaw na siebie!**

Trening, dieta i wirtualny zwierzak, który rozwija się razem z Tobą.

**HackYeah 2026 · Sport & Healthcare**

[O projekcie](#o-projekcie) &nbsp;·&nbsp; [Przetestuj sam](#przetestuj-sam) &nbsp;·&nbsp; [Uruchom lokalnie](#lokalne-uruchomienie) &nbsp;·&nbsp; [Zespół](#nasz-zespół)

</div>

---

## O projekcie

Wejście na siłownię bywa trudniejsze niż sam trening. Nie znasz sprzętu, nie masz planu albo po kilku dniach tracisz chęć do ćwiczeń.

SportPet tworzymy dla osób, które potrzebują pomocy na starcie. Asystenci AI pomagają zaplanować trening i posiłki, wyjaśniają, jak korzystać z maszyn, i pytają o samopoczucie po ćwiczeniach. Wirtualny zwierzak daje dodatkowy powód, żeby wrócić do aplikacji.

Chcemy, żeby regularność wynikała z przyjemności i poczucia postępu. Odpoczynek też jest częścią planu.

## Co znajdziesz w aplikacji?

| Funkcja | Jak z niej korzystasz |
| --- | --- |
| **Plan treningowy i dieta** | Opowiadasz asystentowi o swoich celach i możliwościach. Otrzymujesz plan; kolejne treningi mogą uwzględniać Twój wcześniejszy feedback. |
| **Rozpoznawanie maszyn** | Robisz zdjęcie sprzętu. Dostajesz instrukcję użycia i mapę angażowanych mięśni. Opisy są napisane z myślą o początkujących. |
| **Wywiad po treningu** | Odpowiadasz na krótkie pytania o zmęczenie, motywację, wysiłek i ból. W podsumowaniach sprawdzasz, jak zmienia się Twoje samopoczucie. |
| **Zwierzak i znajomi** | Ukończone treningi pomagają rozwijać zwierzaka. Możesz go karmić, zmieniać jego wygląd i pokazywać go znajomym. |

SportPet pomaga zadbać o aktywność i zauważać własne samopoczucie. Przy niepokojących objawach asystenci sugerują kontakt ze specjalistą; aplikacja nie stawia diagnoz.

> W demo hackathonowym pomiary zdrowotne są syntetyczne. Integracje z zegarkami planujemy w kolejnych wersjach.

---

## Przetestuj sam

**Instructions on how to open project**

1. Pobierz darmową aplikację **Expo Go** ze sklepu **Google Play** (Android) lub **Apple App Store** (iOS).
2. Zeskanuj poniższy kod QR i otwórz projekt w Expo Go. Kod znajdziesz też w naszej prezentacji projektowej (PDF) lub filmiku demo.
3. Zaloguj się na konto demo albo utwórz własne konto.

<div align="center">

<img src="docs/readme/qr.png" alt="Kod QR do aplikacji SportPet" width="220">

</div>

### Adres do wpisania ręcznie

```text
exp://5vmhqvs-anonymous-8081.exp.direct:80
```

### Konto demo

| Email | Hasło |
| --- | --- |
| `guest@mail.pl` | `guestguest` |

Na początek sprawdź plan treningowy, zrób zdjęcie maszyny i odwiedź swojego zwierzaka.

<details>
<summary>Gdy demo nie chce się otworzyć</summary>

Demo działa, gdy serwer Expo i backend są uruchomione. Jeśli adres jest już nieaktualny, poproś nas o nowy kod.

</details>

---

## Lokalne uruchomienie

Potrzebujesz **Dockera z Compose v2**, **Node.js z npm** i dostępu do **Azure OpenAI**.

<details>
<summary><strong>Rozwiń instrukcję uruchomienia na komputerze</strong></summary>

### 1. Konfiguracja backendu

Z katalogu głównego repozytorium skopiuj `backend/.env.example` do `backend/.env`. Jeśli masz już plik env, zachowaj swoją konfigurację.

**PowerShell**

```powershell
Copy-Item backend/.env.example backend/.env
```

**Bash / WSL**

```bash
cp backend/.env.example backend/.env
```

Uzupełnij endpoint i klucz Azure, nazwy deploymentów tekstowego, vision i embeddingów oraz własny `JWT_SECRET`. Deployment vision musi obsługiwać zdjęcia, a modele Vision Agenta — odpowiedzi strukturalne.

Dla lokalnej wersji webowej ustaw:

```dotenv
CORS_ORIGINS=["http://localhost:8081","http://127.0.0.1:8081"]
```

Pliku `.env` nie dodawaj do repozytorium.

### 2. Backend i dane agentów

Z katalogu głównego:

```bash
docker compose up -d --build
docker compose exec backend python -m app.agents.vision.seed --dry-run
docker compose exec backend python -m app.agents.vision.seed
docker compose cp backend/docs_RAG/. backend:/app/docs_RAG
docker compose cp backend/docs_RAG_diet backend:/app/docs_RAG_diet
docker compose exec backend python -m app.rag.ingest --dir /app/docs_RAG --name training
docker compose exec backend python -m app.rag.ingest --dir /app/docs_RAG_diet --name diet
```

| Usługa | Adres |
| --- | --- |
| Backend | http://localhost:8002 |
| Dokumentacja API | http://localhost:8002/docs |

### 3. Frontend

**PowerShell**

```powershell
cd frontend
npm ci
$env:EXPO_PUBLIC_API_URL = "http://localhost:8002/api/v1"
npm run web
```

**Bash / WSL**

```bash
cd frontend
npm ci
EXPO_PUBLIC_API_URL=http://localhost:8002/api/v1 npm run web
```

Otwórz adres pokazany przez Expo, zwykle **http://localhost:8081**, i utwórz konto. Lokalna instalacja nie zawiera konta z publicznego demo.

Na telefonie ustaw adres API na adres komputera dostępny w sieci, np. `http://192.168.1.10:8002/api/v1`, i uruchom `npm start`.

### Aktualizacja i zatrzymanie

| Sytuacja | Polecenie |
| --- | --- |
| Zmiana kodu backendu | `docker compose up -d --build backend` |
| Zmiana pliku env | `docker compose up -d --force-recreate backend` |
| Sprawdzenie logów | `docker compose logs --tail=100 backend` |
| Zatrzymanie usług | `docker compose down` |

`docker compose down` zachowuje dane w wolumenach. Dodanie `-v` je usuwa.

</details>

---

## Nasz zespół

<div align="center">

### Delta Szwadron Super Cool Komando Wilków Alfa

<img src="docs/readme/team.png" alt="Zespół Delta Szwadron Super Cool Komando Wilków Alfa" width="900">

</div>
