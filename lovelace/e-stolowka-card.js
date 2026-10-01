/**
 * Karta Lovelace dla integracji e-Stołówka (loca.pl).
 *
 * Jeden plik bez kroku budowania — wystarczy skopiować go do `config/www/`
 * i dodać jako zasób dashboardu. Czyta sensor tygodniowy integracji
 * (`sensor.<szkoła>_jadlospis_tygodniowy`) i jego atrybut `dni`.
 */

const WEEKDAY_NAMES = [
  "Niedziela",
  "Poniedziałek",
  "Wtorek",
  "Środa",
  "Czwartek",
  "Piątek",
  "Sobota",
];

const MONTH_ABBREVIATIONS = [
  "sty", "lut", "mar", "kwi", "maj", "cze",
  "lip", "sie", "wrz", "paź", "lis", "gru",
];

/** Data „dziś" w lokalnej strefie, w formacie klucza atrybutu `dni`. */
const isoToday = () => {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
};

/** Data z klucza ISO jako obiekt Date w lokalnej strefie (bez przesunięcia UTC). */
const fromIso = (iso) => {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day);
};

/** Poniedziałek i niedziela tygodnia, w którym leży podana data. */
const weekBounds = (iso) => {
  const date = fromIso(iso);
  const weekday = (date.getDay() + 6) % 7; // 0 = poniedziałek
  const start = new Date(date);
  start.setDate(date.getDate() - weekday);
  const end = new Date(date);
  end.setDate(date.getDate() + (6 - weekday));
  const pad = (value) => String(value).padStart(2, "0");
  const format = (value) =>
    `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
  return [format(start), format(end)];
};

/** Rozdziel „nazwa dania (alergeny)" na nazwę i alergeny. */
const splitDish = (dish) => {
  const match = dish.match(/^(.*?)\s*\(([^)]*)\)\s*$/);
  return match
    ? { name: match[1], allergens: match[2] }
    : { name: dish, allergens: "" };
};

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);

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
      (entityId) => entityId.startsWith("sensor.") && entityId.endsWith("_jadlospis_tygodniowy")
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
  _visibleDays() {
    if (!this._config.entity) return { days: [], missingEntity: false };
    const state = this._hass?.states?.[this._config.entity];
    const menuByDate = state?.attributes?.dni;
    if (!menuByDate) return { days: [], missingEntity: !state };

    const today = isoToday();
    const [weekStart, weekEnd] = weekBounds(today);
    const days = Object.keys(menuByDate)
      .sort()
      .filter((dateKey) => {
        if (this._config.range === "all") return true;
        if (this._config.range === "today") return dateKey === today;
        return dateKey >= weekStart && dateKey <= weekEnd;
      })
      .map((dateKey) => ({
        date: dateKey,
        dishes: menuByDate[dateKey].potrawy || [],
        diet: menuByDate[dateKey].dieta || [],
      }));
    return { days, missingEntity: false };
  }

  _subtitle(days) {
    if (days.length === 0) return "";
    const first = fromIso(days[0].date);
    const last = fromIso(days[days.length - 1].date);
    const format = (date) => `${date.getDate()} ${MONTH_ABBREVIATIONS[date.getMonth()]}`;
    return days.length === 1 ? format(first) : `${format(first)} – ${format(last)}`;
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) return;

    const { days, missingEntity } = this._visibleDays();
    const missingConfig = !this._config.entity;
    const today = isoToday();

    const header = `
      <div class="header">
        <div class="icon-badge"><ha-icon icon="mdi:silverware-fork-knife"></ha-icon></div>
        <div class="title-block">
          <div class="title">${escapeHtml(this._config.title)}</div>
          <div class="subtitle">${escapeHtml(this._subtitle(days))}</div>
        </div>
      </div>`;

    let body;
    if (missingConfig) {
      body = this._emptyState("mdi:cog-outline", "Wybierz encję",
        "Wskaż sensor tygodniowy integracji e-Stołówka.");
    } else if (missingEntity) {
      body = this._emptyState("mdi:alert-circle-outline", "Nie znaleziono encji",
        this._config.entity);
    } else if (days.length === 0) {
      body = this._emptyState("mdi:silverware-clean", "Brak jadłospisu",
        "Na ten okres nie opublikowano jeszcze menu.");
    } else {
      body = `<div class="days">${days.map((day) => this._renderDay(day, today)).join("")}</div>`;
    }

    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${header}${body}</ha-card>`;
  }

  _renderDay(day, today) {
    const date = fromIso(day.date);
    const isToday = day.date === today;
    const dishes = day.dishes
      .map((dish) => {
        const { name, allergens } = splitDish(dish);
        const allergenMarkup = allergens
          ? ` <span class="allergens">${escapeHtml(allergens)}</span>`
          : "";
        return `<div class="dish"><span class="dot"></span><span class="name">${escapeHtml(name)}${allergenMarkup}</span></div>`;
      })
      .join("");

    const diet = this._config.show_diet && day.diet.length
      ? `<div class="diet">${day.diet
          .map((variant) => `<span class="chip">${escapeHtml(variant)}</span>`)
          .join("")}</div>`
      : "";

    return `
      <div class="day${isToday ? " today" : ""}">
        <div class="day-head">
          <span>${WEEKDAY_NAMES[date.getDay()]}</span>
          <span class="date">${date.getDate()} ${MONTH_ABBREVIATIONS[date.getMonth()]}</span>
          ${isToday ? '<span class="pill">dziś</span>' : ""}
        </div>
        <div class="dishes">${dishes}</div>
        ${diet}
      </div>`;
  }

  _emptyState(icon, title, detail) {
    return `<div class="empty">
      <ha-icon icon="${icon}"></ha-icon>
      <div class="t1">${escapeHtml(title)}</div>
      <div class="t2">${escapeHtml(detail)}</div>
    </div>`;
  }
}

const SCHEMA = [
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

const LABELS = {
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
      this._form.computeLabel = (schema) => LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: event.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.schema = SCHEMA;
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
