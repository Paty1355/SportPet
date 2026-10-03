# FitApp: frontend

Aplikacja fitness działająca jako strona w przeglądarce i jako aplikacja na telefon (iOS i Android) z jednego kodu.

## Stack

- **Expo SDK 57** + **React Native**, z **react-native-web** dla wersji przeglądarkowej
- **Expo Router** (trasy w `src/app/`)
- **AsyncStorage** do zapamiętywania motywu
- **@expo/vector-icons** (Ionicons) do ikon

Konwencje dla agentów AI są w `AGENTS.md`. Dokumentacja Expo zmienia się między wersjami SDK, więc zawsze sprawdzaj docs dla konkretnej wersji.

## Uruchomienie

```bash
cd frontend
npx expo start --web      # przeglądarka: http://localhost:8081
npx expo start            # telefon: skan QR w Expo Go, ta sama sieć Wi-Fi
npx expo start --tunnel   # telefon przez internet (np. gdy komputer jest zdalnie)
```

Node.js musi być w PATH. Jeśli `npx` nie działa w nowym terminalu, uruchom `$env:Path = "C:\Program Files\nodejs;" + $env:Path`.

## Struktura

```
src/
  app/                 trasy Expo Router (index = kalendarz, training, machines, diet, profile)
  components/          wspólne komponenty (Screen, ComingSoon, NavItemContent, ThemeToggle)
  features/calendar/   kalendarz, siatka miesiąca, lista treningów, modal dodawania
  lib/                 typy (types.ts), daty (dates.ts), motyw (theme.tsx), nawigacja (navItems.ts)
  mocks/               przykładowe dane w kształcie kontraktu API
```

Nawigacja: na telefonie dolny pasek (kalendarz na środku), od 768 px szerokości boczne menu.

## Stan

- Zrobione: nawigacja, przełącznik motywu (jasny/ciemny), kalendarz z dodawaniem treningów (dane lokalne, z mocków).
- Do zrobienia: agent treningowy, rozpoznawanie maszyn (aparat), agent dietetyczny, panel statystyk, podpięcie API.

## Kontrakt danych

`src/lib/types.ts` to kontrakt z zespołem API i agentami. Klucz kalendarza to data `"YYYY-MM-DD"`, a wartość to lista treningów z ćwiczeniami, statusem i źródłem (`agent` albo `user`). Zmiany w typach trzeba uzgodnić z zespołem backendu.

## Backend (planowane)

- Backend w FastAPI w Dockerze, osobno od frontendu. Agenci działają po stronie serwera.
- Frontend łączy się przez HTTP. Adres API będzie w `EXPO_PUBLIC_API_URL`.
- Do ustalenia: adres API dostępny z telefonów, CORS dla wersji webowej, logowanie (tokeny JWT w nagłówku `Authorization`).
- Opcjonalnie: generowanie typów TypeScript z OpenAPI (`openapi-typescript`), żeby typy zawsze zgadzały się z API.

## Demo dla jurorów

- Najprostszy wariant: wersja webowa wdrożona na hosting statyczny, plus backend pod publicznym adresem.
- Alternatywa: opublikowany update przez EAS Update i kod QR w Expo Go.
- Adres API jest wbudowywany w build, więc przy zmianie adresu trzeba opublikować nową wersję.

## Wersja mobilna w przyszłości

Obecny kod nadaje się do zbudowania aplikacji na sklepy bez przepisywania:
- **Build i podpisywanie w chmurze przez EAS Build**, bez lokalnego Xcode i Android Studio (`npx eas-cli@latest build`).
- **Publikacja:** Google Play (jednorazowa opłata developerska), App Store (roczna opłata Apple Developer Program).
- **Aparat do rozpoznawania maszyn** wymaga development buildu, bo Expo Go nie zawiera wszystkich modułów natywnych (`expo-camera`).

## Otwarte pytania

- Nazwa aplikacji (obecnie roboczo "FitApp").
- Wybór ostatecznego kierunku: wersja mobilna w sklepach czy tylko PWA/web.
- Hosting backendu i wersji webowej na demo.
- Model rozpoznawania maszyn: gotowe API, czy model uruchamiany na backendzie.

## Historia decyzji

- Pierwotnie: Vite + React + Tailwind (commit z kalendarzem na branchu `frontend`).
- Zmiana na Expo, bo aplikacja ma działać na telefonie i w przeglądarce z jednego kodu. Logika kalendarza i typy zostały bez zmian.
