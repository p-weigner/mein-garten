/* Node 22: Frontend-Grundfunktionen ohne Browser oder HA-Installation testen. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { test } from "node:test";

const definitions = new Map();
// Simuliert die bereits installierte frühere Gartenkarte: beide Versionen
// müssen gleichzeitig verwendbar bleiben.
const LegacyGardenCard = class {};
definitions.set("mein-garten-card", LegacyGardenCard);
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

test("Neue Karte kollidiert nicht mit der früheren Gartenkarte", () => {
  assert.equal(definitions.get("mein-garten-card"), LegacyGardenCard);
  assert.notEqual(definitions.get("mein-garten-v1-card"), LegacyGardenCard);
  assert.equal(customCards.some((c) => c.type === "mein-garten-card"), false);
});

test("Vollständige Dashboard-YAML verwendet ausschließlich den V1-Typ", () => {
  const dashboard = readFileSync(new URL("../dashboard-mein-garten.yaml", import.meta.url), "utf8");
  assert.ok(dashboard.includes("type: custom:mein-garten-v1-card"));
  assert.ok(!dashboard.includes("type: custom:mein-garten-card"));
});

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


test("Pflegeprofile bieten nur bei echten Texten eine manuell bestätigte Jahreskontrolle", () => {
  const card = buildCard();
  const pflanze = {
    id: "p1", name: "Wald-Hortensie", wissenschaftlich: "Hydrangea arborescens",
    bereich_id: null, gruppe: "Blumen, Stauden und Rosen",
  };
  card._data.pflanzen = [pflanze];
  card._modal = { type: "pflege", existing: pflanze };
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {
    status: "ok",
    felder: {
      pruning: { titel: "Schnitt", text: "<b>unverifiziert</b>" },
      watering: { titel: "Gießen", text: null },
    },
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes('data-action="care-plan"'));
  assert.ok(html.includes('data-field="pruning"'));
  assert.ok(!html.includes('data-field="watering"'));
  assert.ok(html.includes("&lt;b&gt;unverifiziert&lt;/b&gt;"));
  assert.ok(!html.includes("<b>unverifiziert</b>"));

  const clicked = { dataset: { action: "care-plan", id: "p1", field: "pruning" } };
  card._onClick({ target: { closest: () => clicked } });
  assert.equal(card._modal.type, "regel");
  assert.equal(card._modal.prefill.pflanzen_id, "p1");
  assert.equal(card._modal.prefill.rhythmus, "jaehrlich");
  assert.equal(card._modal.prefill.pflegefeld, "pruning");
  assert.ok(card.shadowRoot.innerHTML.includes("nicht fachlich geprüft"));
  assert.ok(card.shadowRoot.innerHTML.includes("Schnittbedarf prüfen"));
});

test("Die Wetter- und iPhone-Schalter sind im Kalender sichtbar und standardmäßig aus", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="automatik-open"'));
  card._modal = { type: "automatik" };
  card._automatik = {
    weather_entity: "weather.home", notify_target: "notify.angelinas_iphone_15_pro",
    freitag_aktiv: false, frost_aktiv: false, frost_grenze_c: 2,
  };
  card._hass = {
    states: { "weather.home": { state: "sunny" }, "notify.angelinas_iphone_15_pro": {} },
    services: { notify: {} },
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("notify.angelinas_iphone_15_pro"));
  assert.ok(html.includes("weather.home"));
  assert.ok(html.includes("Freitags 16:00"));
  assert.ok(!html.includes('name="freitag_aktiv" checked'));
  assert.ok(!html.includes('name="frost_aktiv" checked'));
});


test("Gießkontrolle zeigt zwei Entscheidungen und keine direkte Ein-Klick-Erledigung", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._data.aufgaben = [
    { id: "w1", name: "Gießbedarf prüfen", status: "offen",
      faellig_am: "2026-11-01", aufgabentyp: "giesskontrolle" },
    { id: "t1", name: "Laub entfernen", status: "offen",
      faellig_am: "2026-11-01", aufgabentyp: "einfach" },
  ];
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="task-result" data-id="w1"'));
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="task-done" data-id="t1"'));
  assert.ok(!card.shadowRoot.innerHTML.includes('data-action="task-done" data-id="w1"'));
  const btn = { dataset: { action: "task-result", id: "w1" } };
  card._onClick({ target: { closest: () => btn } });
  assert.equal(card._modal.type, "giessen");
  assert.ok(card.shadowRoot.innerHTML.includes("Kontrolliert – kein Wasser nötig"));
  assert.ok(card.shadowRoot.innerHTML.includes('data-result="gegossen"'));
});

test("Die Wasserentscheidung wird mit eindeutigem Ergebnis ans Backend übergeben", () => {
  const card = buildCard();
  const task = { id: "w1", name: "Gießen", aufgabentyp: "giesskontrolle", status: "offen" };
  card._data.aufgaben = [task];
  card._modal = { type: "giessen", existing: task };
  let sent = null;
  card._mutate = (type, args) => { sent = { type, args }; };
  const btn = {
    dataset: { action: "task-water-choice", id: "w1", result: "kontrolliert_kein_wasser" }
  };
  card._onClick({ target: { closest: () => btn } });
  assert.equal(sent.type, "aufgabe_erledigen");
  assert.equal(sent.args.aufgaben_id, "w1");
  assert.equal(sent.args.ergebnis, "kontrolliert_kein_wasser");
});

test("Abgeschlossene Gießkontrolle zeigt den dokumentierten Pflegezustand", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._data.aufgaben = [
    { id: "w1", name: "Lavendel prüfen", status: "erledigt",
      aufgabentyp: "giesskontrolle", ergebnis: "kontrolliert_kein_wasser",
      faellig_am: "2026-11-01" },
  ];
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("Kontrolliert – kein Wasser nötig"));
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="task-reopen"'));
});

test("Pflegeprofil-Wasser übernimmt die differenzierte Aufgabenart", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Tomate", bereich_id: null };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._care = {
    status: "ok",
    felder: { watering: { titel: "Gießen", text: "Wasserbedarf überprüfen." } }
  };
  const btn = { dataset: { action: "care-plan", id: "p1", field: "watering" } };
  card._onClick({ target: { closest: () => btn } });
  assert.equal(card._modal.prefill.aufgabentyp, "giesskontrolle");
  assert.ok(card.shadowRoot.innerHTML.includes('name="aufgabentyp" value="giesskontrolle"'));
});


test("GBIF-Trivialnamen werden als mehrdeutige Artwahl angezeigt", () => {
  const card = buildCard();
  const plant = {
    wissenschaftlich: "Prunus avium",
    deutsch: "",
    bestaetigt: true,
    quellen: ["GBIF-Trivialnamen"],
  };
  card._modal = { type: "pflanze", existing: null };
  card._suggestions = [plant];
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("Trivialname – Art prüfen"));
  assert.ok(!card._suggestionHTML().includes(">Art bestätigt</span>"));
  assert.ok(card.shadowRoot.innerHTML.includes("Prunus avium"));
});

test("Exakter deutscher Artname bleibt gegenüber dem GBIF-Sammelvorschlag klar bezeichnet", () => {
  const card = buildCard();
  card._modal = { type: "pflanze", existing: null };
  card._suggestions = [
    { wissenschaftlich: "Hydrangea paniculata", deutsch: "Rispenhortensie",
      bestaetigt: true, quellen: ["iNaturalist"] },
    { wissenschaftlich: "Hydrangea arborescens", deutsch: "",
      bestaetigt: true, quellen: ["GBIF-Trivialnamen"] },
  ];
  card._render();
  const html = card._suggestionHTML();
  assert.ok(html.includes("Art bestätigt"));
  assert.ok(html.includes("Trivialname – Art prüfen"));
});
