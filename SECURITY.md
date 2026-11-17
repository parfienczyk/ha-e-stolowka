# Bezpieczeństwo i prywatność

## Co integracja robi z Twoimi danymi

Integracja loguje się na konto rodzica w e-Stołówce Twojej szkoły i czyta
jadłospis. To wszystko.

- E-mail i hasło trafiają **wyłącznie** na serwer Twojej szkoły, tym samym
  formularzem, którego używa przeglądarka.
- Dane logowania przechowuje Home Assistant w swojej konfiguracji, na Twoim
  urządzeniu (`.storage/core.config_entries`).
- Każdy wpis konfiguracyjny ma **własną sesję HTTP i własne ciasteczka**, żeby
  nie mieszać się z sesjami innych integracji ani innych kont.
- Integracja pobiera wyłącznie strony z hosta, który podałeś w konfiguracji.
  Odnośniki znalezione w treści serwisu są sprawdzane pod tym kątem, więc
  spreparowany wpis nie skłoni Home Assistanta do odpytania obcego serwera.
- Nie ma telemetrii, zbierania statystyk ani wysyłania czegokolwiek na serwery
  autora. Projekt nie ma własnego backendu.

## Czego nie wysyłaj publicznie

Strony e-Stołówki zawierają dane dziecka: imię i nazwisko, klasę, rozliczenia
i deklaracje. Dotyczy to też logów w trybie `debug`.

- Nie wklejaj hasła ani zawartości `.env` do zgłoszeń.
- Zrzuty z `dump/` (ze `scripts/explore.py`) przeglądnij i zamaskuj, zanim
  gdziekolwiek je wyślesz. Katalog jest w `.gitignore`.

## Zgłaszanie podatności

Jeśli znajdziesz problem bezpieczeństwa — zwłaszcza coś, co mogłoby ujawnić dane
logowania innych użytkowników — nie otwieraj publicznego zgłoszenia. Użyj
[prywatnego zgłoszenia podatności](https://github.com/parfienczyk/ha-e-stolowka/security/advisories/new)
w zakładce Security.

To projekt hobbystyczny prowadzony po godzinach — nie obiecuję czasu reakcji,
ale przeczytam każde zgłoszenie.
