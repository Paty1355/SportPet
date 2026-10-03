# statistics: wykrywanie trendów w danych zdrowotnych

Moduł liczy deterministyczne statystyki z tabel zdrowotnych (`vital_samples`, `daily_summaries`, `blood_pressure_readings`,
`ecg_recordings`, `cycle_days`). Jego wynik (słownik JSON-owalny) ma zasilać raport dla lekarza i kontekst modelu AI.
Model AI **nie liczy** trendów, tylko opisuje gotową tabelę.

Folder jest w `app/` (import `app.statistics`), a nie w `backend/statistics/`: katalog o nazwie `statistics` w katalogu
roboczym przesłoniłby bibliotekę standardową `statistics`.

```python
from app.statistics import analyze

result = analyze(db, user_id)  # ostatnie 60 pełnych dób UTC (do wczoraj)
result = analyze(db, user_id, end=date(2026, 6, 30), days=40)
```

**Wszystko jest liczone per osoba.** `analyze(db, user_id)` bierze dane jednego użytkownika; linie bazowe, testy i korekta
wielokrotnych porównań (`p_adj`) dotyczą wyłącznie jego szeregów. Nic nie jest agregowane między osobami, a raport dla lekarza
powstaje z jednego wyniku `analyze` dla jednego pacjenta.

Przepływ: `daily.py` (surowe pomiary → 1 wartość na dobę) → `trends.py` (testy) → `analyze.py` (składa wynik, poprawka na wielokrotne testy).
Surowych próbek nie testujemy bezpośrednio: mają rytm dobowy i są autokorelowane, co daje fałszywie małe p-value.

## Pliki i funkcje

### `daily.py`
- `Series`: `dict[date, float]`; doby bez danych nie występują w słowniku.
- `daily_features(db, user_id, start, end)`: cechy dobowe (UTC) dla dób `start`..`end` włącznie. Cecha nie powstaje, gdy doba ma za mało próbek
  (`MIN_SAMPLES = 12` w oknie godzin). Zwracane cechy:

| Cecha | Definicja |
|---|---|
| `rhr` | 10. percentyl tętna w godz. 00–06 (tętno spoczynkowe) |
| `night_dip` | średnie tętno 08–20 minus średnie 00–06 (zanik spadku nocnego jest istotny klinicznie) |
| `stress_day_mean` | średni stres 08–20 |
| `stress_high_frac` | odsetek próbek stresu >60 w godz. 08–20 |
| `spo2_min` | minimum SpO₂ w dobie |
| `spo2_low_count` | liczba próbek SpO₂ <94% |
| `bp_sys`, `bp_dia` | średnie dobowe ciśnienie skurczowe i rozkurczowe |
| `bp_am_pm_diff` | skurczowe rano (<12) minus wieczorem (≥17) |
| `bp_sys_sd_wk` | odchylenie standardowe `bp_sys` w nienakładających się blokach 7 dób liczonych wstecz od `end` (min. 4 wartości w bloku, tylko pełne bloki w oknie); 1 punkt na tydzień, czyli zmienność ciśnienia |
| `steps`, `sleep_minutes` | wartości z `daily_summaries` |
| `ecg_hr` | średni puls z nagrań EKG w dobie |
| `ecg_abnormal` | 1, gdy któraś klasyfikacja EKG ≠ `sinus_rhythm`, inaczej 0 |

- `weekly_sd(daily, start, end, window=7, min_n=4)`: odchylenie standardowe (ddof=1) w nienakładających się blokach `window` dób; wartość stoi na ostatniej dobie bloku. Bloki nie mogą się nakładać, bo kroczące okno dawało fałszywe trendy.
- `cycle_phases(db, user_id, start, end)`: faza cyklu na dobę; pusty słownik dla użytkowników bez cyklu (np. mężczyzn).

### `trends.py` (czyste funkcje numpy/scipy, bez bazy)
- `sen_slope(x, y)`: nachylenie Sena (mediana nachyleń par) + 95% CI. Odporne na wartości odstające.
- `mann_kendall(x, y)`: p-value testu monotonicznego trendu z korektą autokorelacji Hamed–Rao (współczynnik wariancji ≥ 1, więc korekta
  tylko zaostrza). Dla szeregu stałego zwraca 1.0.
- `pettitt(y)`: najbardziej prawdopodobny pojedynczy punkt przełomu (indeks pierwszego punktu nowego reżimu) i p-value.
- `compare(baseline, recent)`: Mann–Whitney U, zwraca p-value i deltę Cliffa (−1..1; dodatnia = ostatnie dni większe niż linia bazowa).
- `robust_z(baseline, values)`: odporny z-score `0.6745·(x − mediana)/MAD` względem linii bazowej; pusty wynik, gdy MAD = 0.
- `lagged_spearman(a, b, lag)`: korelacja Spearmana `a(D)` z `b(D+lag)`; `None`, gdy par <10 lub szereg jest stały.
- `kruskal_by_group(values, groups)`: Kruskal–Wallis między grupami (fazy cyklu), grupy <3 dób są pomijane; `None`, gdy zostaje <2 grup.

### `analyze.py`
- `analyze_series(series, end)`: testy jednej metryki. Wynik `status: "insufficient_data"` (n < 28 dób) albo `ok` z polami `trend`
  (`slope_per_week`, `ci95_per_week`, `p`), `change_point` (`date`, mediany przed/po, `p`), `baseline_vs_recent`
  (mediany, `delta`, `cliffs_delta`, `p`) i `outlier_days` (doby z ostatnich 7 dni z |z| > 2).
- `analyze(db, user_id, end=None, days=60)`: wszystkie metryki z `METRICS`, korelacje opóźnione (`LAG_PAIRS` × lag 0–2 dób: sen→RHR,
  sen→stres, kroki→RHR) i wpływ fazy cyklu na `rhr` i `stress_day_mean`. Do każdego `p` dopisuje `p_adj` (Benjamini–Hochberg), osobno w
  każdej rodzinie testów (trend, przełom, bazowa-vs-ostatnie, korelacje, cykl).

### `charts.py` (wykresy pod PDF: matplotlib + seaborn, statyczne)
Wszystko bierze wynik `analyze(..., include_series=True)` i zwraca `matplotlib.figure.Figure` (albo `None`, gdy nie ma czego rysować).
Figury powstają bez `pyplot`, więc nie ma stanu globalnego ani GUI; szerokość = A4 (8,27 in).
- `plot_metric(name, r)`: szereg dobowy jednej metryki z zaznaczeniem: okna linii bazowej (szare) i ostatnich 7 dób (pomarańczowe) z
  medianami i Δ, prostej trendu Sena (czerwona ciągła = istotny po korekcie, szara przerywana = nieistotny; w podtytule nachylenie,
  95% CI, `p_adj`), istotnego punktu przełomu (fioletowa pionowa + mediany przed/po), dób odstających |z| > 2 (czerwone kropki)
  i progu klinicznego (`REFERENCE`: SpO₂ 94, ciśnienie 135/85, sen 6 h). Przy `insufficient_data` rysuje sam szereg z adnotacją.
- `plot_significance(result)`: słupki −log10(`p_adj`) trendu każdej metryki wobec progu 0,05 (przegląd „co jest istotne”).
- `plot_correlations(result)`: mapa cieplna korelacji Spearmana z opóźnieniem 0–2 doby, `*` = `p_adj` < 0,05.
- `plot_cycle(result)`: mediany metryk w fazach cyklu (punkty, oś nie od zera), `p_adj` Kruskala–Wallisa w tytule.
- `figures(result)`: lista `(nazwa, Figure)` w kolejności: istotność, korelacje, cykl, potem każda metryka z `METRICS`.
- `render_pdf(result, dest)`: PDF (ścieżka lub `BytesIO`), jedna strona na wykres. `to_png(fig, dpi=150)`: bajty PNG pojedynczego wykresu.
- `LABELS` (polskie nazwy i jednostki) i `REFERENCE` (progi) to jedyne miejsce, gdzie trzeba dopisać nową metrykę.

```python
from app.statistics import analyze
from app.statistics.charts import render_pdf, figures, to_png
result = analyze(db, user_id, include_series=True)
render_pdf(result, "raport_wykresy.pdf")          # albo: for name, fig in figures(result): to_png(fig)
```

### Dane pod wykresy i endpoint
- `analyze(..., include_series=True)` dokłada do każdej metryki `series` (`[{date, value}]`, także przy `insufficient_data`) i `trend_line`
  (dwa punkty prostej Sena: pierwsza i ostatnia doba). `baseline_vs_recent` zawiera zawsze `baseline_window` i `recent_window`.
  Bez tej flagi wynik jest zwięzły (nadaje się do kontekstu modelu AI).
- `GET /api/v1/health/stats?days=60&end=YYYY-MM-DD` (`router_charts.py`, JWT, dane zalogowanego użytkownika): to samo z `include_series=True`.
  `days` 7–365, domyślnie 60 (≈40 KB JSON). **Uwaga:** `app/api/v1/router.py` importuje `charts`, a plik nazywa się `router_charts.py`, więc
  dopóki to się nie zgadza, aplikacja się nie uruchomi i endpoint nie jest zarejestrowany.
- `GET /api/v1/health/report` (`health.py`, JWT): PDF z wykresami (`render_pdf`) dla zalogowanego użytkownika, okno domyślne jak w `analyze`.
  Bez tokena 401; gdy żadna metryka nie ma statusu `ok` (za mało danych) 422 z komunikatem.
  `curl -H "Authorization: Bearer <token>" -o raport.pdf http://localhost:8000/api/v1/health/report`

### Okna i minima (stałe w `analyze.py`)
- Trend i przełom: wszystkie doby okna (domyślnie 60), minimum **28 dób z danymi** (`bp_sys_sd_wk`: **8 punktów tygodniowych**, czyli 56 dób; `MIN_POINTS` w `analyze.py`). Mniej: `insufficient_data`, co jest czymś innym niż „brak trendu”.
- „Ostatnie”: 7 dób do `end` włącznie (min. 4 z danymi). Linia bazowa: 28 dób bezpośrednio przed nimi (min. 14 z danymi).
- Domyślny generator (`--days 7`) jest za krótki: do analizy potrzeba np. `--days 60`.
- Kobiety: najlepiej ≥ 1 pełny cykl danych, żeby nie pomylić fazy lutealnej z trendem.

## Progi kliniczne do raportu (jeszcze NIEZAIMPLEMENTOWANE, raport powstanie na końcu)

Do raportu trafia zmiana, która jest istotna statystycznie (`p_adj` < 0,05) **i** przekracza próg kliniczny:

| Metryka | Próg kliniczny |
|---|---|
| RHR (`rhr`) | wzrost ≥ 5 bpm względem linii bazowej albo nachylenie ≥ 1 bpm/tydz. |
| Ciśnienie (`bp_sys`, `bp_dia`; pomiary domowe, ESC) | średnia ≥ 135/85 mmHg; rosnąca zmienność (`bp_sys_sd_wk`) |
| SpO₂ (`spo2_min`, `spo2_low_count`) | powtarzalne wartości < 94%, szczególnie w nocy |
| Sen (`sleep_minutes`) | średnia < 6 h (360 min) albo duża nieregularność |
| EKG (`ecg_abnormal`) | ≥ 2 epizody bradykardii lub tachykardii w 30 dni |
| Nocny spadek pulsu (`night_dip`) | zanik |

Raport per metryka: linia bazowa → ostatnie 7 dni → zmiana → nachylenie na tydzień [95% CI] → `p_adj` → data przełomu → flaga kliniczna;
osobno sekcja korelacji opóźnionych i jawny wpis „brak istotnych zmian” dla pozostałych metryk.

Nie zaimplementowano jeszcze: cosinora pulsu (poziom, amplituda, godzina szczytu), HRV (obecna fala EKG ma stały odstęp R–R).

## Testy

`pytest tests/test_statistics.py` (całość z `--noconftest`, bo `tests/conftest.py` ładuje `app.main`; patrz uwaga o `router.py`): wykrycie trendu i jego CI, data przełomu, szum biały (odsetek fałszywych trendów ≈ 5%), flaga odstającej doby,
`insufficient_data`, przebieg end-to-end z SQLite oraz `include_series` i render PDF (5 stron, JSON-owalność).

## Walidacja na danych z generatora (smoke, 60 dób, SQLite)

Jednorazowy test na `Person.day_payload()` z `generator/generate.py`; 12 osób bez trendu (kontrola negatywna) i 3 z wstrzykniętym
trendem. Osoby są tu tylko powtórzeniami, każda analiza jest niezależna.

- **Kontrola negatywna:** 168 testów trendu, przed korektą p < 0,05 w 13 (7,7%), po korekcie BH w 3. Per osoba: 2 z 12 dostałyby
  w raporcie fałszywą flagę (`bp_sys_sd_7d`, kroczące okno, od tego czasu zastąpione `bp_sys_sd_wk`; u jednej dodatkowo `stress_high_frac`). Korelacje opóźnione i cykl: 0 fałszywych trafień.
- **Trend wstrzyknięty** (`rhr` +0,84/tydz., stres +1,4/tydz., sen −14 min/tydz., skurczowe +1,4 mmHg/tydz.): u wszystkich 3 osób
  wykryte z nachyleniami zgodnymi z wstrzykniętymi (95% CI je obejmuje); kroki bez trendu zostały nieistotne (`p_adj` 0,33–0,80).
  `rhr` wychodzi nieco poniżej 0,84, bo to 10. percentyl pulsu, a nie średnia.

## Znane ograniczenia

- **`bp_sys_sd_wk`** ma tylko 8 punktów na 60 dób, więc test trendu ma ograniczoną moc: wykrywa silny wzrost zmienności (SD 3→18 mmHg) w ok. 72% serii, a słaby może przeoczyć. Fałszywe trendy: ≈3% (kontrola negatywna, 2000 serii). Wcześniejsze kroczące okno 7 dób dawało ≈17% (nakładające się dane), dlatego zastąpiono je blokami. `baseline_vs_recent` i `outlier_days` dla tej cechy są puste (1 punkt w ostatnim tygodniu).
- Cechy pochodne od tej samej serii (`stress_day_mean` i `stress_high_frac`, `bp_sys` i `bp_sys_sd_wk`) nie są niezależnymi testami,
  a korekta BH traktuje je jak niezależne.
- Pettitt zwraca jeden punkt przełomu (największy); p-value jest przybliżone.
