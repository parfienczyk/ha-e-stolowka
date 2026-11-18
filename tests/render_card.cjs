/**
 * Renderuje kartę na atrapie DOM i sprawdza, że tekst z encji
 * nie wchodzi do HTML jako znacznik.
 *
 * Uruchamiane z tests/test_card.py. Sam plik karty jest skryptem
 * przeglądarkowym, więc podstawiamy minimum, którego dotyka przy starcie.
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const defined = {};
const RealDate = Date;
const FIXED_MS = RealDate.parse("2026-11-16T23:30:00Z");

function FakeDate(...args) {
  if (args.length === 0) return new RealDate(FIXED_MS);
  return new RealDate(...args);
}
FakeDate.now = () => FIXED_MS;
FakeDate.parse = RealDate.parse;
FakeDate.UTC = RealDate.UTC;

const context = {
  console,
  Intl,
  Date: FakeDate,
  HTMLElement: class {
    constructor() {
      this.shadowRoot = null;
      this.classList = { toggle() {} };
    }

    attachShadow() {
      this.shadowRoot = { innerHTML: "" };
      return this.shadowRoot;
    }
  },
  customElements: {
    define(name, cls) {
      defined[name] = cls;
    },
  },
  document: {
    createElement() {
      return {};
    },
  },
};
context.window = context;
context.globalThis = context;

vm.createContext(context);
vm.runInContext(
  fs.readFileSync(
    path.join(__dirname, "../lovelace/e-stolowka-card.js"),
    "utf8",
  ),
  context,
  { filename: "e-stolowka-card.js" },
);

const entity = "sensor.szkola_jadlospis_tygodniowy";
const card = new defined["e-stolowka-card"]();
card.setConfig({
  entity,
  title: "TYTUL<script>",
  range: "all",
  show_diet: true,
});
card.hass = {
  themes: {},
  states: {
    [entity]: {
      attributes: {
        dni: {
          "2026-10-06": {
            potrawy: ["DANIE<img src=x>"],
            dieta: ["DIETA<script>"],
          },
        },
      },
    },
  },
};

const html = card.shadowRoot.innerHTML;
const raw = ["<script", "<img"];
for (const needle of raw) {
  if (html.toLowerCase().includes(needle)) {
    console.error(`Surowy HTML (${needle}):\n${html}`);
    process.exit(1);
  }
}

const escaped = ["TYTUL&lt;script&gt;", "DANIE&lt;img", "DIETA&lt;script&gt;"];
for (const needle of escaped) {
  if (!html.includes(needle)) {
    console.error(`Brak escapowania (${needle}):\n${html}`);
    process.exit(1);
  }
}

const zoneCard = new defined["e-stolowka-card"]();
zoneCard.setConfig({ entity, range: "today" });
zoneCard.hass = {
  themes: {},
  config: { time_zone: "Europe/Warsaw" },
  states: {
    [entity]: {
      attributes: {
        dni: {
          "2026-11-16": { potrawy: ["OBIAD-16"], dieta: [] },
          "2026-11-17": { potrawy: ["OBIAD-17"], dieta: [] },
        },
      },
    },
  },
};
const zoneHtml = zoneCard.shadowRoot.innerHTML;
if (!zoneHtml.includes("OBIAD-17") || zoneHtml.includes("OBIAD-16")) {
  console.error(`Zła data „dziś" dla Europy/Warszawy:\n${zoneHtml}`);
  process.exit(1);
}

let renders = 0;
const proto = defined["e-stolowka-card"].prototype;
const originalRender = proto._render;
proto._render = function renderCounted() {
  renders += 1;
  return originalRender.call(this);
};
const skipCard = new defined["e-stolowka-card"]();
skipCard.setConfig({ entity, range: "all" });
skipCard.hass = zoneCard.hass;
const afterFirst = renders;
skipCard.hass = zoneCard.hass;
if (renders !== afterFirst) {
  console.error(`Karta rysowała się ponownie: ${renders} zamiast ${afterFirst}`);
  process.exit(1);
}

const changedHass = {
  ...zoneCard.hass,
  states: {
    [entity]: {
      attributes: { dni: { "2026-11-17": { potrawy: ["OBIAD-NOWY"], dieta: [] } } },
    },
  },
};
skipCard.hass = changedHass;
if (renders !== afterFirst + 1 || !skipCard.shadowRoot.innerHTML.includes("OBIAD-NOWY")) {
  console.error("Karta nie przerysowała się po zmianie stanu encji");
  process.exit(1);
}

const staleCard = new defined["e-stolowka-card"]();
staleCard.setConfig({ entity, range: "week" });
staleCard.hass = {
  ...zoneCard.hass,
  states: {
    [entity]: {
      attributes: {
        dni: {
          "2026-11-09": { potrawy: ["STARE"], dieta: [] },
          "2026-11-13": { potrawy: ["STARE"], dieta: [] },
        },
      },
    },
  },
};
if (!staleCard.shadowRoot.innerHTML.includes("Najnowszy pobrany jadłospis: 9 lis – 13 lis")) {
  console.error(`Pusta karta nie pokazuje zakresu pobranych dni:\n${staleCard.shadowRoot.innerHTML}`);
  process.exit(1);
}
