/* Node 22: Frontend-Grundfunktionen ohne Browser oder HA-Installation testen. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { test } from "node:test";

const definitions = new Map();
const customCards = [];

class FakeHTMLElement {
  attachShadow() {
    this.shadowRoot = {
      innerHTML: "",
      addEventListener: () => {},
      querySelector: () => null,
    };
    return this.shadowRoot;
  }
}

const sandbox = {
  HTMLElement: FakeHTMLElement,
  window: {
    customCards,
    confirm: () => true,
    prompt: () => null,
  },
  customElements: {
    get: (name) => definitions.get(name),
    define: (name, klass) => definitions.set(name, klass),
  },
  Date,
  setTimeout,
  clearTimeout,
  console,
};

const js = readFileSync(new URL("../mein-garten-card.js", import.meta.url), "utf8");
runInNewContext(js, sandbox, { filename: "mein-garten-card.js" });
const Card = definitions.get("mein-garten-v1-card");

function buildCard() {
  const card = new Card();
  card.setConfig({});
  card._groups = [
    "Blumen, Stauden und Rosen",
    "Gemüse und Kräuter",
    "Obst und Beeren",
  ];
  card._data = {
    version: 1,
    pflanzen: [],
    bereiche: [],
    aufgaben: [],
    historie: [],
  };
  card._render();
  return card;
}

test("Karte wird als eigenes Lovelace-Element registriert", () => {
  assert.equal(typeof Card, "function");
  assert.equal(customCards.find((c) => c.type === "mein-garten-v1-card").name, "Mein Garten");
});

test("Alle vier vereinbarten Ansichten sind vorhanden", () => {
  const card = buildCard();
  const html = card.shadowRoot.innerHTML;
  for (const tab of ["Start", "Pflanzen", "Kalender", "Bereiche"]) {
    assert.ok(html.includes(tab), "Fehlender Reiter: " + tab);
  }
  assert.ok(html.includes("Dein Garten. Alles im Blick."));
});

test("Eigene Pflanzen erscheinen ohne fest programmierten Artenkatalog", () => {
  const card = buildCard();
  card._tab = "pflanzen";
  card._data.pflanzen.push({
    id: "p1", name: "Japanische Pfingstrose",
    wissenschaftlich: "Paeonia lactiflora",
    gruppe: "Blumen, Stauden und Rosen",
    bereich_id: null,
    notizen: "Seltene Sorte",
  });
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Paeonia lactiflora"));
  assert.ok(html.includes("Japanische Pfingstrose"));
  assert.ok(html.includes("Nicht zugeordnet"));
});

test("Pflanzenbeschriftungen werden HTML-sicher dargestellt", () => {
  const card = buildCard();
  card._tab = "pflanzen";
  card._data.pflanzen.push({
    id: "p1", name: "<img src=x onerror=alert(1)>",
    wissenschaftlich: "Hydrangea macrophylla",
    gruppe: null, bereich_id: null, notizen: "<script>alert(1)</script>",
  });
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("&lt;img"));
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes("<img src=x"));
  assert.ok(!html.includes("<script>alert(1)</script>"));
});

test("Pflanzenformular mit deutscher Suche, Gruppe, Bereich und Notizen", () => {
  const card = buildCard();
  card._modal = { type: "pflanze", existing: null };
  card._render();
  const html = card.shadowRoot.innerHTML;
  for (const expected of [
    "Bauernhortensie", "wissenschaftlich", "gruppe", "bereich_id", "notizen",
    "Pflanze hinzufügen"
  ]) assert.ok(html.includes(expected), expected);
});

test("Unsichere Pflanzenzuordnung wird kenntlich gemacht", () => {
  const card = buildCard();
  card._modal = { type: "pflanze", existing: null };
  card._suggestions = [
    { wissenschaftlich: "Hydrangea macrophylla", deutsch: "Gartenhortensie",
      bestaetigt: true },
    { wissenschaftlich: "Hydrangea paniculata", deutsch: "Rispenhortensie",
      bestaetigt: false },
  ];
  const html = card._suggestionHTML();
  assert.ok(html.includes("Art bestätigt"));
  assert.ok(html.includes("Bitte Art prüfen"));
});

test("Manuelle Aufgabe hat Erledigungs- und Wiederöffnen-Aktion", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._data.aufgaben = [
    { id: "t1", name: "Gießen", status: "offen", faellig_am: "2026-11-02", pflanzen_id: null },
    { id: "t2", name: "Düngen", status: "erledigt", faellig_am: "2026-10-01", pflanzen_id: null },
  ];
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes('data-action="task-done"'));
  assert.ok(html.includes('data-action="task-reopen"'));
  assert.ok(html.includes("02.11.2026"));
});

test("Gartenbereiche lassen sich separat verwalten", () => {
  const card = buildCard();
  card._tab = "bereiche";
  card._data.bereiche = [{ id: "a1", name: "Hochbeet" }];
  card._data.pflanzen = [{
    id: "p1", name: "Tomate", wissenschaftlich: "Solanum lycopersicum",
    bereich_id: "a1", gruppe: "Gemüse und Kräuter"
  }];
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Hochbeet"));
  assert.ok(html.includes("1 Pflanzen zugeordnet"));
  assert.ok(html.includes('data-action="area-rename"'));
});

test("Externe Suche sendet nur den Suchbegriff an die eigene WS-API", async () => {
  const card = buildCard();
  card._modal = { type: "pflanze", existing: null };
  card._query = "Bauernhortensie";
  card._searchGeneration = 1;
  let received;
  card._call = async (type, args) => {
    received = { type, args };
    return { pflanzen: [], quellenstatus: [] };
  };
  await card._search(1);
  assert.equal(received.type, "pflanzen_suchen");
  assert.equal(received.args.suchbegriff, "Bauernhortensie");
});

test("Erfolgreicher Schreibbefehl aktualisiert gespeicherten Zustand", async () => {
  const card = buildCard();
  card._call = async (type, args) => {
    assert.equal(type, "bereich_anlegen");
    assert.equal(args.name, "Terrasse");
    return {
      daten: {
        ...card._data,
        bereiche: [{ id: "a1", name: "Terrasse" }]
      },
      gruppen: card._groups
    };
  };
  await card._mutate("bereich_anlegen", { name: "Terrasse" });
  assert.equal(card._data.bereiche[0].name, "Terrasse");
});

test("Wiederkehrende HA-State-Updates erzeugen keine doppelten Abos", async () => {
  const card = buildCard();
  let subscribeCount = 0;
  const connection = {
    subscribeMessage: async () => {
      subscribeCount++;
      return () => {};
    },
  };
  const ha = { connection, callWS: async () => ({}) };
  card._connected = true;
  card.hass = ha;
  card.hass = ha;
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(subscribeCount, 1);
  card.disconnectedCallback();
});
