## Co zmienia

<!-- Jedno-dwa zdania. Jeśli PR zamyka zgłoszenie, napisz "Closes #123". -->

## Jak to sprawdziłem

<!--
Zaznacz, co uruchomiłeś. Parser da się testować bez Home Assistanta:

    pip install -r requirements-test.txt
    pytest tests/ -q
    ruff check . && ruff format --check .
-->

- [ ] `pytest tests/ -q`
- [ ] `ruff check .` i `ruff format --check .`
- [ ] Sprawdziłem na własnej instalacji Home Assistanta
- [ ] Zmiana dotyczy parsera i dołożyłem test na nowy układ strony

## Obsługa innej szkoły

<!-- Wypełnij tylko, jeśli PR dodaje wsparcie dla kolejnej szkoły. -->

- Adres: <!-- https://... -->
- Co było inne: <!-- np. inna ścieżka listy aktualności, jadłospis w tabeli -->

> Nie dodawaj do repo zrzutów stron z danymi uczniów. Jako fixture wklej
> okrojony fragment HTML bez imion, klas i rozliczeń.
