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
const context = {
  console,
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
