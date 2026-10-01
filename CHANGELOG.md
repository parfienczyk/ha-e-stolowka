# Historia zmian

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/).
Projekt stosuje [wersjonowanie semantyczne](https://semver.org/lang/pl/).

## [Niewydane]

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

[Niewydane]: https://github.com/parfienczyk/ha-e-stolowka/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/parfienczyk/ha-e-stolowka/releases/tag/v0.1.0
