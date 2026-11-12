# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/).
Projekt stosuje [wersjonowanie semantyczne](https://semver.org/lang/pl/).

## [Niewydane]

## [0.5.1] — 2026-11-12

### Naprawione

- Zły port albo urwane IPv6 w adresie strony z jadłospisem pokazują błąd
  formularza, zamiast wywalać ekran opcji.

## [0.5.0] — 2026-11-12

### Dodane

- Publiczna strona szkoły jako główne źródło jadłospisu. Dni, których na niej
  nie ma, uzupełnia e-Stołówka, a awaria jednego źródła nie gasi drugiego.
  Dla `sobolewosp.loca.pl` adres ustawia się sam; inne szkoły mogą podać swój
  w opcjach integracji, a puste pole wyłącza to źródło.

### Zmienione

- Gdy hasło do e-Stołówki przestanie działać, a strona szkoły działa, encje
  zostają dostępne i Home Assistant tylko prosi o nowe hasło. Do tego czasu
  integracja nie próbuje logować się ponownie odrzuconym hasłem.

### Naprawione

- Parser pomija boczne menu strony (`<aside>`), które inaczej doklejałoby się
  do potraw z ostatniego dnia.
- Adres wskazujący PDF zamiast strony HTML daje czytelny błąd w logu, zamiast
  wyłączać encje.

## [0.4.1] — 2026-10-21

### Naprawione

- Wpisy ze słowem między datami w adresie (`jadlospis-191026-do-231026`)
  znów są rozpoznawane. Bez tego integracja nie startowała z błędem
  „Żadna ze stron … nie zawiera wpisów z jadłospisem”.

## [0.4.0] — 2026-10-06

### Dodane

- Blueprint automatyzacji: o 7:30 powiadomienie z jadłospisem na dziś.
  Pomija dni bez menu i, domyślnie, weekendy.

## [0.3.1] — 2026-10-06

### Naprawione

- Wpisy, w których adres ma kilka myślników między datami
  (`jadlospis-051026---091026`), znów są rozpoznawane. Szkoła tak zapisuje
  tydzień, gdy w tytule między datami jest spacja (`05.10.26 - 09.10.26`).
  Bez tego bieżący tydzień wypadał z listy i karta zostawała pusta.

## [0.3.0] — 2026-10-01

### Zmienione

- Domyślna częstotliwość odpytywania to teraz **raz na dobę**, nie co 6 godzin.
  Jadłospis publikowany jest raz w tygodniu, a encje „dziś” i „jutro” przeliczają
  się o północy niezależnie od odpytywania — częstsze pytanie obciążało serwer
  szkoły, nic nie wnosząc. Jeśli nie ustawiałeś tej opcji ręcznie, po aktualizacji
  Twoja instalacja przejdzie na dobowy interwał. Zakres w Opcjach pozostaje 1–24
  godziny.

## [0.2.0] — 2026-10-01

### Bezpieczeństwo

- Odnośniki do jadłospisu wykryte w treści serwisu muszą teraz wskazywać ten sam
  host, co skonfigurowany adres szkoły. Wcześniej spreparowany wpis w serwisie
  mógł skłonić Home Assistanta do odpytania dowolnego hosta z sieci domowej
  użytkownika (ciasteczka sesji i tak by nie wyciekły — słoik aiohttp jest
  związany z domeną — ale samo żądanie było wysyłane).
- Log diagnostyczny nie zawiera już adresu e-mail. Logi `debug` bywają wklejane
  do publicznych zgłoszeń.

### Dodane

- Karta Lovelace (`lovelace/e-stolowka-card.js`) z edytorem wizualnym.
- Testy uruchamiane na Pythonie 3.13 i 3.14; Dependabot pilnuje wersji akcji
  i zależności testowych.

## [0.1.0] — pierwsza wersja

Pierwsze wydanie. Integracja pobiera jadłospis szkolnej stołówki z platformy
e-Stołówka (loca.pl) i udostępnia go w Home Assistancie.

### Dodane

- Konfiguracja z interfejsu (adres szkoły, e-mail i hasło rodzica), z ponownym
  logowaniem, gdy hasło przestanie działać.
- Trzy sensory: jadłospis na dziś, na jutro i cały pobrany tydzień.
- Warianty dietetyczne (`DIETA:`) jako osobny atrybut `dieta`; alergeny
  zostają w nazwach potraw.
- Odświeżanie stanu o północy — bez dodatkowego ruchu sieciowego.
- Konfigurowalna częstotliwość odpytywania (domyślnie co 6 godzin).
- Tłumaczenia polskie i angielskie.
- `scripts/explore.py` — rozpoznanie układu serwisu w innej szkole.

### Jak to działa

Jadłospis nie ma na loca.pl własnego modułu — szkoła publikuje go jako wpisy
w aktualnościach, po jednym na tydzień, z zakresem dat w adresie. Integracja
czyta listę aktualności, wybiera wpisy obejmujące dzisiejszą datę (bieżący
tydzień i następny) i tylko je pobiera. Obsługiwany jest układ akapitowy
(nagłówek dnia + potrawy) oraz tabelaryczny.

[Niewydane]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.5.1...HEAD
[0.5.1]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/parfienczyk/ha-e-stolowka/releases/tag/v0.1.0
