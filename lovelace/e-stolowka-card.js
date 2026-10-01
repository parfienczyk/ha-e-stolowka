/**
 * Karta Lovelace dla integracji e-Stołówka (loca.pl).
 *
 * Jeden plik bez kroku budowania — wystarczy skopiować go do `config/www/`
 * i dodać jako zasób dashboardu. Czyta sensor tygodniowy integracji
 * (`sensor.<szkoła>_jadlospis_tygodniowy`) i jego atrybut `dni`.
 */

const NAZWY_DNI = [
  "Niedziela",
  "Poniedziałek",
  "Wtorek",
  "Środa",
  "Czwartek",
  "Piątek",
  "Sobota",
];

const MIESIACE_SKROT = [
  "sty", "lut", "mar", "kwi", "maj", "cze",
  "lip", "sie", "wrz", "paź", "lis", "gru",
];

/** Data „dziś" w lokalnej strefie, w formacie klucza atrybutu `dni`. */
function isoDzis() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** Data z klucza ISO jako obiekt Date w lokalnej strefie (bez przesunięcia UTC). */
function zIso(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/** Poniedziałek i niedziela tygodnia, w którym leży podana data. */
function granice(iso) {
  const d = zIso(iso);
  const dzien = (d.getDay() + 6) % 7; // 0 = poniedziałek
  const od = new Date(d);
  od.setDate(d.getDate() - dzien);
  const do_ = new Date(d);
  do_.setDate(d.getDate() + (6 - dzien));
  const p = (n) => String(n).padStart(2, "0");
  const fmt = (x) => `${x.getFullYear()}-${p(x.getMonth() + 1)}-${p(x.getDate())}`;
  return [fmt(od), fmt(do_)];
}

/** Rozdziel „nazwa dania (alergeny)" na nazwę i alergeny. */
function rozdziel(potrawa) {
  const m = potrawa.match(/^(.*?)\s*\(([^)]*)\)\s*$/);
  return m ? { nazwa: m[1], alergeny: m[2] } : { nazwa: potrawa, alergeny: "" };
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const STYLE = `
  :host {
    --es-brand: #2e8f57;
    --es-brand-strong: #1f6b40;
    --es-brand-bg: #e1f3e7;
    --es-chip-bg: rgba(46, 143, 87, 0.08);
    --es-dot: #b4c4ba;
  }
  :host(.dark) {
    --es-brand: #5fc98a;
    --es-brand-strong: #8fdcaa;
    --es-brand-bg: rgba(95, 201, 138, 0.16);
    --es-chip-bg: rgba(255, 255, 255, 0.06);
    --es-dot: #5c6b62;
  }

  ha-card {
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 13px;
  }
  :host(.compact) ha-card { padding: 10px 12px; gap: 8px; }
  :host(.compact) .subtitle { display: none; }
  :host(.compact) .icon-badge { width: 26px; height: 26px; border-radius: 7px; }
  :host(.compact) .icon-badge ha-icon { --mdc-icon-size: 16px; }

  .header { display: flex; align-items: center; gap: 11px; }
  .icon-badge {
    width: 36px; height: 36px; border-radius: 10px; flex: none;
    background: var(--es-brand-bg); color: var(--es-brand);
    display: flex; align-items: center; justify-content: center;
  }
  .title-block { min-width: 0; flex: 1; }
  .title { font-size: 0.95rem; font-weight: 700; line-height: 1.25; }
  .subtitle { font-size: 0.76rem; color: var(--secondary-text-color); margin-top: 1px; }

  .days { display: flex; flex-direction: column; gap: 10px; }

  .day { display: flex; flex-direction: column; gap: 4px; }
  .day-head {
    display: flex; align-items: center; gap: 7px;
    font-size: 0.66rem; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: var(--secondary-text-color);
  }
  .day.today .day-head { color: var(--es-brand-strong); }
  .day-head .date { font-variant-numeric: tabular-nums; font-weight: 600; opacity: 0.8; }
  .pill {
    font-size: 0.58rem; font-weight: 800; letter-spacing: 0.03em;
    background: var(--es-brand); color: #fff;
    padding: 1px 6px; border-radius: 999px; text-transform: uppercase;
  }

  .dishes { display: flex; flex-direction: column; gap: 2px; }
  .dish {
    display: flex; gap: 8px; align-items: flex-start;
    font-size: 0.78rem; line-height: 1.35;
  }
  .day.today .dish { font-weight: 600; }
  .dot {
    width: 5px; height: 5px; border-radius: 50%; flex: none;
    margin-top: 7px; background: var(--es-dot);
  }
  .day.today .dot { background: var(--es-brand); }
  .dish .name { min-width: 0; }
  .allergens {
    color: var(--secondary-text-color);
    font-size: 0.68rem; font-weight: 400; opacity: 0.85;
  }
  .diet {
    margin-top: 3px; display: flex; flex-wrap: wrap; gap: 5px;
  }
  .diet .chip {
    background: var(--es-chip-bg); color: var(--secondary-text-color);
    border-radius: 999px; padding: 2px 8px;
    font-size: 0.64rem; font-weight: 600;
  }

  .empty {
    display: flex; flex-direction: column; align-items: center;
    gap: 8px; padding: 20px 16px; text-align: center;
    color: var(--secondary-text-color);
  }
  .empty ha-icon { --mdc-icon-size: 28px; opacity: 0.7; }
  .empty .t1 { font-size: 0.9rem; font-weight: 600; color: var(--primary-text-color); }
  .empty .t2 { font-size: 0.76rem; max-width: 28ch; }
`;

class EStolowkaCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("e-stolowka-card-editor");
  }

  /** Szkielet dla wyszukiwarki kart — podpowiada pierwszy pasujący sensor. */
  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(
      (e) => e.startsWith("sensor.") && e.endsWith("_jadlospis_tygodniowy")
    );
    return { type: "custom:e-stolowka-card", entity: entity || "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    if (config && config.range && !["week", "all", "today"].includes(config.range)) {
      throw new Error('range musi być jednym z: "week", "all", "today"');
    }
    this._config = {
      title: "Stołówka",
      range: "week",
      show_diet: false,
      compact: false,
      ...config,
    };
    this.classList.toggle("compact", Boolean(this._config.compact));
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this.classList.toggle("dark", Boolean(hass?.themes?.darkMode));
    this._render();
  }

  getCardSize() {
    return 4;
  }

  /** Dni do pokazania, już przefiltrowane i posortowane. */
  _dni() {
    if (!this._config.entity) return { lista: [], brakEncji: false };
    const stan = this._hass?.states?.[this._config.entity];
    const dni = stan?.attributes?.dni;
    if (!dni) return { lista: [], brakEncji: !stan };

    const dzis = isoDzis();
    const [od, do_] = granice(dzis);
    const lista = Object.keys(dni)
      .sort()
      .filter((d) => {
        if (this._config.range === "all") return true;
        if (this._config.range === "today") return d === dzis;
        return d >= od && d <= do_;
      })
      .map((data) => ({ data, ...dni[data] }));
    return { lista, brakEncji: false };
  }

  _podtytul(lista) {
    if (lista.length === 0) return "";
    const a = zIso(lista[0].data);
    const b = zIso(lista[lista.length - 1].data);
    const f = (d) => `${d.getDate()} ${MIESIACE_SKROT[d.getMonth()]}`;
    return lista.length === 1 ? f(a) : `${f(a)} – ${f(b)}`;
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) return;

    const { lista, brakEncji } = this._dni();
    const brakKonfiguracji = !this._config.entity;
    const dzis = isoDzis();

    const naglowek = `
      <div class="header">
        <div class="icon-badge"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon></div>
        <div class="title-block">
          <div class="title">${esc(this._config.title)}</div>
          <div class="subtitle">${esc(this._podtytul(lista))}</div>
        </div>
      </div>`;

    let tresc;
    if (brakKonfiguracji) {
      tresc = this._pusto("mdi:cog-outline", "Wybierz encję",
        "Wskaż sensor tygodniowy integracji e-Stołówka.");
    } else if (brakEncji) {
      tresc = this._pusto("mdi:alert-circle-outline", "Nie znaleziono encji",
        this._config.entity);
    } else if (lista.length === 0) {
      tresc = this._pusto("mdi:silverware-clean", "Brak jadłospisu",
        "Na ten okres nie opublikowano jeszcze menu.");
    } else {
      tresc = `<div class="days">${lista.map((d) => this._dzien(d, dzis)).join("")}</div>`;
    }

    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${naglowek}${tresc}</ha-card>`;
  }

  _dzien(dzien, dzis) {
    const d = zIso(dzien.data);
    const dzisiaj = dzien.data === dzis;
    const potrawy = (dzien.potrawy || [])
      .map((p) => {
        const { nazwa, alergeny } = rozdziel(p);
        const a = alergeny ? ` <span class="allergens">${esc(alergeny)}</span>` : "";
        return `<div class="dish"><span class="dot"></span><span class="name">${esc(nazwa)}${a}</span></div>`;
      })
      .join("");

    const dieta = this._config.show_diet && (dzien.dieta || []).length
      ? `<div class="diet">${dzien.dieta
          .map((x) => `<span class="chip">${esc(x)}</span>`)
          .join("")}</div>`
      : "";

    return `
      <div class="day${dzisiaj ? " today" : ""}">
        <div class="day-head">
          <span>${NAZWY_DNI[d.getDay()]}</span>
          <span class="date">${d.getDate()} ${MIESIACE_SKROT[d.getMonth()]}</span>
          ${dzisiaj ? '<span class="pill">dziś</span>' : ""}
        </div>
        <div class="dishes">${potrawy}</div>
        ${dieta}
      </div>`;
  }

  _pusto(ikona, t1, t2) {
    return `<div class="empty">
      <ha-icon icon="${ikona}"></ha-icon>
      <div class="t1">${esc(t1)}</div>
      <div class="t2">${esc(t2)}</div>
    </div>`;
  }
}

const SCHEMAT = [
  {
    name: "entity",
    required: true,
    selector: { entity: { domain: "sensor", integration: "e_stolowka" } },
  },
  { name: "title", selector: { text: {} } },
  {
    name: "range",
    selector: {
      select: {
        mode: "dropdown",
        options: [
          { value: "week", label: "Bieżący tydzień" },
          { value: "all", label: "Wszystkie pobrane dni" },
          { value: "today", label: "Tylko dziś" },
        ],
      },
    },
  },
  { name: "show_diet", selector: { boolean: {} } },
  { name: "compact", selector: { boolean: {} } },
];

const ETYKIETY = {
  entity: "Sensor tygodniowy",
  title: "Tytuł karty",
  range: "Zakres dni",
  show_diet: "Pokaż warianty dietetyczne",
  compact: "Tryb kompaktowy",
};

/** Formularz konfiguracji karty w interfejsie Home Assistanta. */
class EStolowkaCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._config || !this._hass) return;
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (s) => ETYKIETY[s.name] || s.name;
      this._form.addEventListener("value-changed", (ev) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = SCHEMAT;
    this._form.data = this._config;
  }
}

customElements.define("e-stolowka-card-editor", EStolowkaCardEditor);
customElements.define("e-stolowka-card", EStolowkaCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "e-stolowka-card",
  name: "e-Stołówka",
  description: "Jadłospis szkolnej stołówki z platformy loca.pl",
  preview: true,
});

console.info("%c e-STOLOWKA-CARD %c 0.1.0 ", "background:#2e8f57;color:#fff;border-radius:3px 0 0 3px", "background:#1f6b40;color:#fff;border-radius:0 3px 3px 0");
