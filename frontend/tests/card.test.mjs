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


test("Gefundene Schreibvariante wird nicht als eindeutig zugeordnete Art dargestellt", () => {
  const card = buildCard();
  card._modal = { type: "pflanze", existing: null };
  card._suggestions = [
    { wissenschaftlich: "Hydrangea paniculata",
      deutsch: "Rispen-Hortensie", bestaetigt: true,
      quellen: ["iNaturalist", "Schreibvariante"] },
  ];
  card._render();
  assert.ok(card._suggestionHTML().includes("Namensvariante – Art prüfen"));
  assert.ok(!card._suggestionHTML().includes('>Art bestätigt</span>'));
  const el = { dataset: { action: "suggestion", index: "0" } };
  let noteText = "";
  const form = {
    elements: {
      namedItem: (key) => ({ value: key === "name" ? "Rispenhortensie" : "" }),
    },
  };
  const textNode = { set textContent(v) { noteText = v; } };
  card.shadowRoot.querySelector = (selector) =>
    selector === 'form[data-form="pflanze"]' ? form :
      selector === "#garten-artenhinweis" ? textNode : null;
  card._onClick({ target: { closest: () => el } });
  assert.ok(noteText.includes("bitte die tatsächliche Art prüfen"));
});


test("Der Saisonkalender zeigt nur manuell zu bestätigende Fenster", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._saison = {
    anker: {last_frost: "2027-05-15", first_frost: ""},
    vorschlaege: [{
      pflanzen_id: "p1", pflanze: "<Tomate>", wissenschaftlich: "Solanum lycopersicum",
      katalog_id: "tomato", titel: "Vorziehen prüfen",
      fenster_von: "2027-03-20", fenster_bis: "2027-04-03",
      vorgemerkt: false, quelle: "OpenPlantDB", lizenz: "CC0 1.0",
    }],
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Saisonfenster"));
  assert.ok(html.includes("Vorziehen prüfen"));
  assert.ok(html.includes("20.03.2027"));
  assert.ok(html.includes("OpenPlantDB"));
  assert.ok(html.includes("Kontrolle planen"));
  assert.ok(html.includes("&lt;Tomate&gt;"));
  assert.ok(!html.includes("<Tomate>"));
  assert.ok(!html.includes("Automatisch aussäen"));
});

test("Fehlender Frostanker erzeugt keine kontrollierbare Saisonaufgabe", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._saison = {
    anker: {last_frost: "", first_frost: ""},
    vorschlaege: [{
      pflanzen_id: "p1", pflanze: "Tomate", wissenschaftlich: "Solanum lycopersicum",
      katalog_id: "tomato", titel: "Vorziehen prüfen",
      fenster_von: null, fenster_bis: null,
      fehlender_anker: "last_frost", vorgemerkt: false,
    }],
  };
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("Frost-Referenzdatum"));
  assert.ok(!card.shadowRoot.innerHTML.includes('data-action="saison-plan"'));
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="saisonanker-open"'));
});

test("Saisonfenster kann erst nach eigener Terminwahl angelegt werden", () => {
  const card = buildCard();
  const r = {
    pflanzen_id: "p1", pflanze: "Tomate", wissenschaftlich: "Solanum lycopersicum",
    katalog_id: "tomato", titel: "Vorziehen prüfen",
    fenster_von: "2027-03-20", fenster_bis: "2027-04-03", vorgemerkt: false,
  };
  card._data.pflanzen = [{id: "p1", name: "Tomate"}];
  card._saison = {anker: {last_frost: "2027-05-15", first_frost: ""},
    vorschlaege: [r]};
  card._tab = "kalender";
  card._render();
  const btn = {dataset: {action: "saison-plan", id: "p1", katalog: "tomato"}};
  card._onClick({target: {closest: () => btn}});
  assert.equal(card._modal.type, "saison");
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes('name="datum"'));
  assert.ok(html.includes('min="2027-03-20"'));
  assert.ok(html.includes('max="2027-04-03"'));
  assert.ok(html.includes("Als Kontrolle vormerken"));

  let called = null;
  card._mutate = (type, args) => {called = {type, args};};
  const form = {
    dataset: {form: "saison"},
    elements: {namedItem: (name) =>
      name === "datum" ? {value: "2027-03-25"} : {value: ""}},
  };
  card._onSubmit({target: form, preventDefault: () => {}});
  assert.equal(called.type, "saison_vormerken");
  assert.deepEqual(JSON.parse(JSON.stringify(called.args)), {
    pflanzen_id: "p1", katalog_id: "tomato", datum: "2027-03-25",
  });
});

test("Vorgemerkte Saisonaufgabe ist gegen erneuten Klick gesperrt", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._saison = {anker: {last_frost: "2027-05-15", first_frost: ""},
    vorschlaege: [{
      pflanzen_id: "p1", pflanze: "Tomate",
      wissenschaftlich: "Solanum lycopersicum",
      katalog_id: "tomato", titel: "Vorziehen prüfen",
      fenster_von: "2027-03-20", fenster_bis: "2027-04-03",
      vorgemerkt: true,
    }]};
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Vorgemerkt"));
  assert.ok(html.includes('disabled'));
  const btn = {dataset: {action: "saison-plan", id: "p1", katalog: "tomato"}};
  card._onClick({target: {closest: () => btn}});
  assert.equal(card._modal, null);
});

test("Frost-Referenzdaten lassen sich ohne API-Schlüssel konfigurieren", () => {
  const card = buildCard();
  card._saison = {anker: {last_frost: "2027-05-15", first_frost: ""},
    vorschlaege: []};
  card._modal = {type: "saisonanker"};
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes('name="last_frost"'));
  assert.ok(card.shadowRoot.innerHTML.includes('value="2027-05-15"'));
  assert.ok(card.shadowRoot.innerHTML.includes("Eine US-Klimazone wird nicht"));
  assert.ok(!card.shadowRoot.innerHTML.includes("API-Key"));
});


test("Die tatsächliche Saisonabdeckung eigener Pflanzen bleibt sichtbar", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._data.pflanzen = [
    {id: "p1", name: "Tomate", wissenschaftlich: "Solanum lycopersicum"},
    {id: "p2", name: "<Rispenhortensie>", wissenschaftlich: "Hydrangea paniculata"},
  ];
  card._saison = {
    katalog_arten: 1292,
    anker: {last_frost: "2027-05-15", first_frost: ""},
    vorschlaege: [{
      pflanzen_id: "p1", pflanze: "Tomate", wissenschaftlich: "Solanum lycopersicum",
      katalog_id: "tomato", titel: "Vorziehen prüfen",
      fenster_von: "2027-03-20", fenster_bis: "2027-04-03",
      vorgemerkt: false,
    }],
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Für 1 von 2 erfassten Pflanzen"));
  assert.ok(html.includes("1292 botanische Arten"));
  assert.ok(html.includes("&lt;Rispenhortensie&gt;"));
  assert.ok(!html.includes("<Rispenhortensie>"));
  assert.ok(html.includes("weiterhin mit eigenen Aufgaben"));
});


test("Vergangene Saisonfenster werden nicht erneut zur Planung angeboten", () => {
  const card = buildCard();
  card._tab = "kalender";
  const proposal = {
    pflanzen_id: "p1", pflanze: "Tomate",
    wissenschaftlich: "Solanum lycopersicum", katalog_id: "tomato",
    titel: "Vorziehen prüfen", fenster_von: "2027-03-20",
    fenster_bis: "2027-04-03", abgelaufen: true, vorgemerkt: false,
  };
  card._data.pflanzen = [{id: "p1", name: "Tomate"}];
  card._saison = {
    anker: {last_frost: "2027-05-15", first_frost: ""},
    katalog_arten: 1292,
    vorschlaege: [proposal],
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("bereits in der Vergangenheit"));
  assert.ok(html.includes("Vergangen"));
  assert.ok(html.includes('data-action="saison-plan"'));
  assert.match(html, /data-action="saison-plan"[^>]*disabled/);
  const btn = {dataset: {action: "saison-plan", id: "p1", katalog: "tomato"}};
  card._onClick({target: {closest: () => btn}});
  assert.equal(card._modal, null);
});


test("Pflanzenkarten öffnen eine eigene Entwicklungsansicht ohne neuen Hauptreiter", () => {
  const card = buildCard();
  card._tab = "pflanzen";
  card._data.pflanzen = [{
    id: "p1", name: "Gartenrose", wissenschaftlich: "Rosa canina",
    bereich_id: null, gruppe: "Blumen, Stauden und Rosen",
  }];
  card._data.beobachtungen = [{
    id: "b1", pflanzen_id: "p1", phase: "bluete_beginn",
    beobachtet_am: "2025-06-15", notiz: "",
  }];
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="entwicklung-open"'));
  assert.ok(card.shadowRoot.innerHTML.includes("Zuletzt beobachtet"));
  assert.ok(card.shadowRoot.innerHTML.includes("Blütebeginn"));
  assert.ok(!card.shadowRoot.innerHTML.includes('data-tab="entwicklung"'));
  const btn = { dataset: { action: "entwicklung-open", id: "p1" } };
  card._onClick({ target: { closest: () => btn } });
  assert.equal(card._modal.type, "entwicklung");
  assert.ok(card.shadowRoot.innerHTML.includes("Pflanzenentwicklung: Gartenrose"));
});

test("Entwicklungsphase enthält Datum, sieben Stufen und keine Pflegefreigabe", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla" };
  card._data.pflanzen = [plant];
  card._modal = { type: "entwicklung", existing: plant };
  card._render();
  const html = card.shadowRoot.innerHTML;
  for (const stage of [
    "Austrieb", "Knospenbildung", "Blütebeginn", "Fruchtansatz",
    "Fruchtreife", "Laubfärbung", "Blattfall",
  ]) assert.ok(html.includes(stage), stage);
  assert.ok(html.includes('data-form="entwicklung"'));
  assert.ok(html.includes('name="beobachtet_am"'));
  assert.ok(html.includes('type="date"'));
  assert.ok(html.includes("keine automatischen Pflege"));
  assert.ok(!html.includes("Schnitt freigeben"));
});

test("Entwicklungsbeobachtung sendet nur eigene IDs, Phase, Datum und Notiz", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla" };
  card._data.pflanzen = [plant];
  card._modal = { type: "entwicklung", existing: plant };
  let captured = null;
  card._mutate = (type, args) => { captured = { type, args }; };
  const values = {
    phase: "knospenbildung", beobachtet_am: "2025-04-12",
    notiz: "Erste Knospen an der Terrasse",
  };
  const form = {
    dataset: { form: "entwicklung" },
    elements: { namedItem: (name) => ({ value: values[name] || "" }) },
  };
  card._onSubmit({ target: form, preventDefault: () => {} });
  assert.equal(captured.type, "beobachtung_anlegen");
  assert.deepEqual(JSON.parse(JSON.stringify(captured.args)), {
    pflanzen_id: "p1", phase: "knospenbildung",
    beobachtet_am: "2025-04-12", notiz: "Erste Knospen an der Terrasse",
  });
  assert.equal(captured.args.person, undefined);
  assert.equal(captured.args.quelle, undefined);
});

test("Entwicklungsverlauf zeigt Jahre getrennt ohne Wetterprognose zu erfinden", () => {
  const card = buildCard();
  const plant = {
    id: "p1", name: "Bauernhortensie",
    wissenschaftlich: "Hydrangea macrophylla",
  };
  card._data.pflanzen = [plant];
  card._data.beobachtungen = [
    { id: "b1", pflanzen_id: "p1", phase: "bluete_beginn",
      beobachtet_am: "2025-06-01", wissenschaftlich: "Hydrangea macrophylla" },
    { id: "b2", pflanzen_id: "p1", phase: "bluete_beginn",
      beobachtet_am: "2026-05-27", wissenschaftlich: "Hydrangea macrophylla" },
    { id: "b3", pflanzen_id: "p1", phase: "fruchtreife",
      beobachtet_am: "2025-10-10", wissenschaftlich: "Hydrangea macrophylla" },
  ];
  card._modal = { type: "entwicklung", existing: plant };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Frühester von dir dokumentierter Blütebeginn"));
  assert.ok(html.includes("27.05.2026"));
  assert.ok(html.includes("01.06.2025"));
  assert.ok(html.includes("keine Vorhersagen"));
  assert.ok(html.includes("Fruchtreife"));
});

test("Entwicklungsnotizen werden HTML-sicher dargestellt und Einträge gelöscht", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla" };
  card._data.pflanzen = [plant];
  card._data.beobachtungen = [{
    id: "b1", pflanzen_id: "p1", phase: "austrieb",
    beobachtet_am: "2025-04-01",
    notiz: "<img src=x onerror=alert(1)>",
    person: "<script>unsafe</script>",
    wissenschaftlich: "Hydrangea macrophylla",
  }];
  card._modal = { type: "entwicklung", existing: plant };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("&lt;img"));
  assert.ok(!html.includes("<img src=x"));
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes("<script>unsafe"));
  const btn = { dataset: { action: "beobachtung-remove", id: "b1" } };
  let called = null;
  card._mutate = (type, args) => { called = { type, args }; };
  card._onClick({ target: { closest: () => btn } });
  assert.equal(called.type, "beobachtung_entfernen");
  assert.deepEqual(JSON.parse(JSON.stringify(called.args)), { beobachtung_id: "b1" });
});

test("Kalender zeigt tatsächliche Beobachtungen getrennt von Aufgaben", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._data.pflanzen = [{ id: "p1", name: "Kirschbaum" }];
  card._data.beobachtungen = [{
    id: "b1", pflanzen_id: "p1", phase: "bluete_beginn",
    beobachtet_am: "2025-04-10", notiz: "Erste Blüte",
  }];
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Eigene Pflanzenbeobachtungen"));
  assert.ok(html.includes("Kirschbaum"));
  assert.ok(html.includes("10.04.2025"));
  assert.ok(html.includes('data-action="entwicklung-open"'));
  assert.ok(html.includes("Keine offenen Aufgaben"));
});

test("Alte Gartendaten ohne Beobachtungen sind weiterhin lesbar", () => {
  const card = buildCard();
  card._data.beobachtungen = undefined;
  card._data.pflanzen = [{ id: "p1", name: "Lavendel", bereich_id: null }];
  card._tab = "pflanzen";
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("Lavendel"));
  assert.ok(card.shadowRoot.innerHTML.includes('data-action="entwicklung-open"'));
});


test("DWD-Referenz zeigt beobachtete Regionaldaten und Quellen statt Pflegeratschläge", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._dwd = {
    quelle: "Deutscher Wetterdienst (DWD), Climate Data Center",
    lizenz: "CC BY 4.0",
    abgerufen_am: "2026-10-30",
    regionen: {
      nordost: {label: "Nordostdeutsches Referenzgebiet (grob, 52,0–54,2° N / 12–15° O)"},
      deutschland: {label: "Deutschlandweite DWD-Beobachtungsstationen"},
    },
    werte: [
      {
        indikator: "hasel_bluete", pflanze: "Hasel (Arten nicht unterschieden)",
        phase: "Blütebeginn", region: "nordost", jahr: 2026,
        median: "2026-02-20", quartil_von: "2026-02-13",
        quartil_bis: "2026-02-25", stationen: 16,
      },
      {
        indikator: "hasel_bluete", pflanze: "Hasel (Arten nicht unterschieden)",
        phase: "Blütebeginn", region: "deutschland", jahr: 2026,
        median: "2026-02-12", quartil_von: "2026-02-06",
        quartil_bis: "2026-02-20", stationen: 130,
      },
    ],
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("DWD: Jahreszeiten im Vergleich"));
  assert.ok(html.includes("Nordostdeutsches Referenzgebiet"));
  assert.ok(html.includes("20.02.2026"));
  assert.ok(html.includes("16 Stationen"));
  assert.ok(html.includes("mittlere 50 %"));
  assert.ok(html.includes("nur formal geprüft"));
  assert.ok(html.includes("CC BY 4.0"));
  assert.ok(html.includes("30.10.2026"));
  assert.ok(html.includes("Originaldaten"));
  assert.ok(html.includes("keine automatische Pflegeempfehlung"));
  assert.ok(!html.includes("130 Stationen"));
  assert.ok(!html.includes("Jetzt schneiden"));
  assert.ok(!html.includes("Automatisch düngen"));
});

test("DWD-Vergleichsgebiet lässt sich ohne Netz- oder Nutzerdatenänderung wechseln", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._dwd = {
    abgerufen_am: "2026-10-30",
    regionen: {
      nordost: {label: "Nordost"},
      deutschland: {label: "Deutschland"},
    },
    werte: [
      {
        indikator: "forsythie_bluete", pflanze: "Forsythie",
        phase: "Blütebeginn", region: "nordost", jahr: 2025,
        median: "2025-03-25", quartil_von: "2025-03-24",
        quartil_bis: "2025-03-27", stationen: 23,
      },
      {
        indikator: "forsythie_bluete", pflanze: "Forsythie",
        phase: "Blütebeginn", region: "deutschland", jahr: 2025,
        median: "2025-03-12", quartil_von: "2025-03-04",
        quartil_bis: "2025-03-20", stationen: 166,
      },
    ],
  };
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("25.03.2025"));
  let requests = [];
  card._call = (...args) => {requests.push(args);};
  const select = {dataset: {action: "dwd-region", region: "deutschland"}};
  card._onClick({target: {closest: () => select}});
  assert.equal(card._dwdRegion, "deutschland");
  assert.ok(card.shadowRoot.innerHTML.includes("12.03.2025"));
  assert.ok(card.shadowRoot.innerHTML.includes("166 Stationen"));
  assert.ok(!card.shadowRoot.innerHTML.includes("23 Stationen"));
  assert.deepEqual(requests, []);
  const wrong = {dataset: {action: "dwd-region", region: "privatadresse"}};
  card._onClick({target: {closest: () => wrong}});
  assert.equal(card._dwdRegion, "deutschland");
});

test("Abwesende DWD-Daten beeinflussen weder Pflanzen noch Aufgaben", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._dwd = null;
  card._data.aufgaben = [{
    id: "t1", name: "Eigene Kontrolle",
    status: "offen", faellig_am: "2026-11-02",
  }];
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Eigene Kontrolle"));
  assert.ok(!html.includes("DWD: Jahreszeiten im Vergleich"));
});

test("DWD-Beobachtungslabels werden HTML-sicher dargestellt", () => {
  const card = buildCard();
  card._tab = "kalender";
  card._dwd = {
    abgerufen_am: "2026-10-30",
    regionen: {
      nordost: {label: '<script>alert(1)</script>'},
      deutschland: {label: "Deutschland"},
    },
    werte: [{
      indikator: "hasel_bluete", pflanze: '<img src=x onerror=alert(1)>',
      phase: "Blütebeginn", region: "nordost", jahr: 2026,
      median: "2026-03-01", quartil_von: "2026-02-27",
      quartil_bis: "2026-03-03", stationen: 9,
    }],
  };
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("&lt;img"));
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes("<script>alert(1)</script>"));
  assert.ok(!html.includes("<img src=x"));
});


test("10k-CC0-Standort-Steckbrief ist sofort sichtbar, auch wenn OpenPlantbook lädt", () => {
  const card = buildCard();
  const plant = {
    id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina",
  };
  card._data.pflanzen = [plant];
  card._standort = {
    katalog_arten: 10642,
    quell_commit: "c6287784527ebb4162e242394ee08f46d338218b",
    quelle: "OpenPlantDB", lizenz: "CC0 1.0",
    profile: {
      p1: {
        wissenschaftlich: "Rosa canina",
        merkmale: {
          sun: "full", water: "low",
          frost_tolerance: "hardy", season: "perennial",
        },
      },
    },
  };
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = true;
  card._care = null;
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Standort-Steckbrief"));
  assert.ok(html.includes("Rosa canina"));
  assert.ok(html.includes("Sonnig"));
  assert.ok(html.includes("Eher gering"));
  assert.ok(html.includes("frosttolerant"));
  assert.ok(html.includes("Mehrjährig"));
  assert.ok(html.includes("Deutsche Pflegeinformationen werden geladen"));
  assert.ok(html.includes("keine automatischen Pflegeaufgaben"));
  assert.ok(!html.includes("Jährliche Kontrolle dazu planen"));
});

test("OpenPlantbook-Ausfall entfernt keine kostenlosen CC0-Standortmerkmale", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Sommerflieder", wissenschaftlich: "Buddleja davidii"};
  card._data.pflanzen = [plant];
  card._standort = {
    quell_commit: "c6287784527ebb4162e242394ee08f46d338218b",
    profile: { p1: {wissenschaftlich: "Buddleja davidii",
      merkmale: {sun: "full", water: "low", season: "perennial"}} },
  };
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {status: "quelle_nicht_eingerichtet", felder: {}};
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Standort-Steckbrief"));
  assert.ok(html.includes("Sonnig"));
  assert.ok(html.includes("OpenPlantbook ist nicht eingerichtet"));
});

test("Widersprüchliche CC0-Wasserangaben werden nicht als Gießintervall erfunden", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla"};
  card._data.pflanzen = [plant];
  card._standort = {
    quell_commit: "c6287784527ebb4162e242394ee08f46d338218b",
    profile: {p1: {
      wissenschaftlich: "Hydrangea macrophylla",
      merkmale: {sun: "partial", frost_tolerance: "hardy", season: "perennial"},
    }},
  };
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {status: "art_nicht_gefunden", felder: {}};
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Halbschattig"));
  assert.ok(!html.includes("Wasserbedarf laut Quelle"));
  assert.ok(html.includes("kein Gießintervall"));
  assert.ok(!html.includes("Jetzt gießen"));
});

test("Unbekannte botanische Arten bekommen keine Merkmale anderer Pflanzen", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Felsenbirne", wissenschaftlich: "Amelanchier lamarckii"};
  card._data.pflanzen = [plant];
  card._standort = {katalog_arten: 10642, profile: {}};
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {status: "art_nicht_gefunden", felder: {}};
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Standort-Steckbrief"));
  assert.ok(html.includes("keine eindeutig verwendbaren Standortmerkmale"));
  assert.ok(!html.includes("Wasserbedarf laut Quelle"));
});

test("Veränderte Pflanzenart macht den alten Standort-Steckbrief ungültig", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Rose", wissenschaftlich: "Rosa gallica"};
  card._data.pflanzen = [plant];
  card._standort = {profile: {p1: {
    wissenschaftlich: "Rosa canina",
    merkmale: {sun: "full", water: "low"},
  }}};
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = true;
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("keine eindeutig verwendbaren Standortmerkmale"));
  assert.ok(!html.includes("Lichtbedarf laut Quelle"));
});

test("Standort-Steckbrief bleibt optional bei alten Garten-Datenständen", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Lavendel", wissenschaftlich: "Lavandula angustifolia"};
  card._data.pflanzen = [plant];
  card._standort = null;
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {status: "quelle_nicht_eingerichtet", felder: {}};
  card._render();
  assert.ok(card.shadowRoot.innerHTML.includes("OpenPlantbook ist nicht eingerichtet"));
  assert.ok(!card.shadowRoot.innerHTML.includes("Standort-Steckbrief"));
});

test("Botanische Namen aus dem Standort-Snapshot sind HTML-escaped", () => {
  const card = buildCard();
  const species = 'Rosa <img src=x onerror=alert(1)>';
  const plant = {id: "p1", name: "Rose", wissenschaftlich: species};
  card._data.pflanzen = [plant];
  card._standort = {
    quell_commit: "c6287784527ebb4162e242394ee08f46d338218b",
    profile: {p1: {wissenschaftlich: species,
      merkmale: {sun: "full"}}},
  };
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = true;
  card._render();
  const html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("&lt;img"));
  assert.ok(!html.includes('<img src=x onerror'));
  assert.ok(!html.includes("automatisches Gießen"));
});


test("Pflegewissen zeigt eigene Notizen lokal und HTML-sicher trotz Quellenausfall", () => {
  const card = buildCard();
  card._carePlant = "p1";
  card._data.pflanzen = [{
    id: "p1", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla",
    notizen: '<script>alert("privat")</script>',
  }];
  card._care = { status: "quelle_nicht_erreichbar", felder: {} };
  const html = card._careHTML();
  assert.ok(html.includes("Deine Pflanzennotizen"));
  assert.ok(html.includes("&lt;script&gt;"));
  assert.ok(!html.includes('<script>alert("privat")</script>'));
  assert.ok(html.includes('data-action="plant-edit" data-id="p1"'));
  assert.ok(html.includes("OpenPlantbook ist momentan nicht erreichbar"));
  assert.ok(!html.includes("Automatisch übersetzt, nicht fachlich geprüft"));
});

test("Teilweise übersetzte Pflegehinweise zeigen nur echte Texte statt Leer-Karten", () => {
  const card = buildCard();
  card._carePlant = "p2";
  card._data.pflanzen = [{
    id: "p2", name: "Rose", wissenschaftlich: "Rosa canina", notizen: "",
  }];
  card._care = {
    status: "teilweise", felder: {
      watering: {titel: "Gießen", text: "Bei Bedarf kontrollieren.", status: "maschinenuebersetzt"},
      pruning: {titel: "Schnitt", text: null, status: "keine_angabe"},
      fertilization: {titel: "Düngung", text: null, status: "uebersetzung_ausstehend"},
    },
  };
  const html = card._careHTML();
  assert.ok(html.includes("Bei Bedarf kontrollieren."));
  assert.ok(html.includes("Maschinell übersetzt"));
  assert.ok(html.includes("2 von 3 Pflegefeldern"));
  assert.ok(!html.includes("Keine Angabe verfügbar."));
  assert.ok(html.includes("data-action=\"care-plan\""));
});

test("Keine deutschen Pflegefreitexte führen zu ehrlicher Meldung und Notiz-Zugriff", () => {
  const card = buildCard();
  card._carePlant = "p3";
  card._data.pflanzen = [{
    id: "p3", name: "Felsenbirne", wissenschaftlich: "Amelanchier lamarckii", notizen: "",
  }];
  card._care = { status: "kein_deutscher_text", felder: {
    sunlight: {titel: "Licht und Standort", text: null, status: "keine_angabe"},
  }};
  const html = card._careHTML();
  assert.ok(html.includes("Keine weiteren deutschen Pflegehinweise"));
  assert.ok(html.includes('data-action="plant-edit" data-id="p3"'));
  assert.ok(html.includes("1 von 1 Pflegefeldern"));
  assert.ok(!html.includes('data-action="care-plan"'));
});

test("Während des Übersetzens bleiben lokale Pflanzennotizen sichtbar", () => {
  const card = buildCard();
  card._carePlant = "p4";
  card._data.pflanzen = [{
    id: "p4", name: "Lavendel", wissenschaftlich: "Lavandula angustifolia",
    notizen: "Standort am Zaun",
  }];
  card._careLoading = true;
  const html = card._careHTML();
  assert.ok(html.includes("Standort am Zaun"));
  assert.ok(html.includes("Deutsche Pflegeinformationen werden geladen"));
});


test("Pflegewissen erlaubt gezielten erneuten Abruf mit eindeutigem Flag", async () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina", notizen: "" };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = { status: "teilweise", felder: {
    watering: { titel: "Gießen", text: "Bisheriger Hinweis" },
  }};
  let request;
  card._call = async (type, args) => {
    request = { type, args };
    return { status: "ok", felder: {
      watering: { titel: "Gießen", text: "Neuer Hinweis", status: "maschinenuebersetzt" },
    }};
  };
  assert.ok(card._careHTML().includes('data-action="care-refresh"'));
  const clicked = { disabled: false, dataset: { action: "care-refresh", id: "p1" } };
  card._onClick({ target: { closest: () => clicked } });
  assert.equal(request.type, "pflegeprofil");
  assert.equal(request.args.pflanzen_id, "p1");
  assert.equal(request.args.aktualisieren, true);
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(card._careLoading, false);
  assert.ok(card._careHTML().includes("Neuer Hinweis"));
  assert.ok(!card._careHTML().includes("Bisheriger Hinweis"));
});

test("Während einer erneuten Quellenprüfung bleiben die bisherigen Hinweise sichtbar", async () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._care = { status: "ok", felder: {
    watering: { titel: "Gießen", text: "Vorheriger deutscher Hinweis" },
  }};
  let release;
  card._call = () => new Promise((resolve) => { release = resolve; });
  const clicked = { disabled: false, dataset: { action: "care-refresh", id: "p1" } };
  card._onClick({ target: { closest: () => clicked } });
  assert.equal(card._careLoading, true);
  const inProgress = card._careHTML();
  assert.ok(inProgress.includes("Vorheriger deutscher Hinweis"));
  assert.ok(inProgress.includes("Aktualisierung läuft"));
  assert.ok(inProgress.includes('data-action="care-refresh" data-id="p1" disabled'));
  release({ status: "ok", felder: {
    watering: { titel: "Gießen", text: "Aktualisiert" },
  }});
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.equal(card._careLoading, false);
  assert.ok(card._careHTML().includes("Aktualisiert"));
});

test("Quellenfehler verrät keine technischen Details und bewahrt bestehendes Pflegewissen", async () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._care = { status: "ok", felder: {
    pruning: { titel: "Schnitt", text: "Nicht bestätigte deutsche Notiz" },
  }};
  card._call = async () => { throw new Error("Authorization: secret-token"); };
  const clicked = { disabled: false, dataset: { action: "care-refresh", id: "p1" } };
  card._onClick({ target: { closest: () => clicked } });
  await new Promise((resolve) => setTimeout(resolve, 0));
  const html = card._careHTML();
  assert.ok(html.includes("Nicht bestätigte deutsche Notiz"));
  assert.ok(html.includes("erneute Abruf ist fehlgeschlagen"));
  assert.ok(!html.includes("secret-token"));
});

test("Alter Pflegecache ist bei Quellenfehler transparent als nicht bestätigt markiert", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._care = {
    status: "ok", abgerufen_utc: "2026-10-10T12:00:00+00:00",
    aktualisierung: "quelle_nicht_erreichbar",
    felder: { watering: { titel: "Gießen", text: "Altbestand" }},
  };
  const html = card._careHTML();
  assert.ok(html.includes("OpenPlantbook ist momentan nicht erreichbar"));
  assert.ok(html.includes("Altbestand"));
  assert.ok(html.includes("10.10.2026"));
  assert.ok(html.includes("nicht neu bestätigt"));
});

test("Nur der aktuelle geöffnete Pflanzendialog darf Pflegequellen erneut prüfen", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._modal = { type: "pflege", existing: plant };
  card._carePlant = "p1";
  card._careLoading = false;
  let calls = 0;
  card._call = () => { calls++; return Promise.resolve({}); };
  const clicked = { disabled: false, dataset: { action: "care-refresh", id: "p2" } };
  card._onClick({ target: { closest: () => clicked } });
  assert.equal(calls, 0);
  assert.equal(card._careLoading, false);
});


test("Teilantwort: alter Schnitt wird von aktuellen Gießhinweisen sichtbar getrennt", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina"};
  card._data.pflanzen = [plant];
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._careLoading = false;
  card._care = {
    status: "teilweise", veraltete_felder: 1,
    felder: {
      watering: {titel: "Gießen", text: "Aktueller deutscher Text",
        status: "original_deutsch", belegt_utc: "2026-10-30T14:00:00+00:00"},
      pruning: {titel: "Schnitt", text: "Älterer deutscher Text",
        status: "zwischengespeichert", quellstatus: "uebersetzung_ausstehend",
        zuletzt_bestaetigt_utc: "2026-10-01T10:00:00+00:00"},
    },
  };
  const html = card._careHTML();
  assert.ok(html.includes("Aktueller deutscher Text"));
  assert.ok(html.includes("Älterer deutscher Text"));
  assert.ok(html.includes("01.10.2026"));
  assert.ok(html.includes("nicht erneut aus der Quelle bestätigt"));
  assert.ok(html.includes("1 Pflegefeld stammt nur aus älteren"));
  assert.ok(html.includes('<span class="chip warning">Ältere Information</span>'));
  assert.ok(html.includes('data-field="watering"'));
  assert.ok(!html.includes('data-field="pruning"'));
  assert.ok(!html.includes("Keine Angabe verfügbar."));
});

test("Historische Pflegefelder können auch durch manipulierte Klicks keinen neuen Termin anlegen", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina"};
  card._data.pflanzen = [plant];
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._care = {
    status: "teilweise",
    felder: {
      pruning: {titel: "Schnitt", text: "Nicht neu bestätigter Schnitt",
        status: "zwischengespeichert"},
    },
  };
  card._onClick({target: {closest: () => ({
    disabled: false, dataset: {action: "care-plan", id: "p1", field: "pruning"},
  })}});
  assert.equal(card._modal.type, "pflege");
});

test("Nach vollständigem Quellenfehler werden alle alten Pflegehinweise nur angezeigt", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Rosa canina", wissenschaftlich: "Rosa canina"};
  card._data.pflanzen = [plant];
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._care = {
    status: "ok", aktualisierung: "quelle_nicht_erreichbar",
    abgerufen_utc: "2026-10-01T10:00:00+00:00",
    felder: {watering: {titel: "Gießen", text: "Älterer Cachetext",
      status: "maschinenuebersetzt"}},
  };
  const html = card._careHTML();
  assert.ok(html.includes("Älterer Cachetext"));
  assert.ok(html.includes("nicht neu bestätigt"));
  assert.ok(!html.includes('data-action="care-plan"'));
  card._onClick({target: {closest: () => ({
    disabled: false, dataset: {action: "care-plan", id: "p1", field: "watering"},
  })}});
  assert.equal(card._modal.type, "pflege");
});

test("Unerwartete Feldinhalte werden nicht als HTML in historischem Datum interpretiert", () => {
  const card = buildCard();
  const plant = {id: "p1", name: "Hundsrose", wissenschaftlich: "Rosa canina"};
  card._data.pflanzen = [plant];
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._care = {status: "teilweise", felder: {
    pruning: {titel: "<img src=x onerror=alert(1)>",
      text: "<script>unsafe</script>", status: "zwischengespeichert",
      zuletzt_bestaetigt_utc: "<img src=x onerror=alert(1)>"},
  }};
  const html = card._careHTML();
  assert.ok(html.includes("&lt;script&gt;unsafe&lt;/script&gt;"));
  assert.ok(html.includes("&lt;img src=x onerror=alert(1)&gt;"));
  assert.ok(!html.includes("<script>unsafe</script>"));
  assert.ok(!html.includes("<img src=x onerror=alert(1)>"));
  assert.ok(!html.includes("Text zuletzt aus der Quelle abgerufen am "));
});


test("EIVE-Europa zeigt fünf Indikatoren mit Quellbelegen ohne neue Pflegeanweisungen", () => {
  const card = buildCard();
  const plant = {
    id: "p1", name: "Hasel", wissenschaftlich: "Corylus avellana", notizen: "Privat",
  };
  card._data.pflanzen = [plant];
  card._modal = {type: "pflege", existing: plant};
  card._carePlant = "p1";
  card._eive = {
    quelle: "EIVE 1.0", lizenz: "CC BY 4.0",
    profile: {p1: {wissenschaftlich: "Corylus avellana", indikatoren: {
      L: {wert: 6.12, quellsysteme: 20},
      M: {wert: 4.45, quellsysteme: 24},
      N: {wert: 5.2, quellsysteme: 18},
      R: {wert: 6.2, quellsysteme: 21},
      T: {wert: 4.3, quellsysteme: 1},
    }}},
  };
  card._care = {status: "quelle_nicht_erreichbar", felder: {}};
  const html = card._careHTML();
  for (const expected of [
    "Europäische Standortindikatoren", "Bodenfeuchtigkeit",
    "Nährstoffverfügbarkeit", "Bodenreaktion", "Temperatur",
    "6,1 / 10", "4,5 / 10", "24 Quellsysteme",
    "Nur 1 Quellsystem", "CC BY 4.0", "10.5281/zenodo.7534792",
    "keine Dünge-", "Keine weiteren deutschen Pflegehinweise",
  ]) assert.ok(html.includes(expected), expected);
  assert.ok(!card._eiveHTML().includes('data-action="care-plan"'));
});

test("EIVE-Quelle bleibt optional und überträgt nicht verwandte Pflanzenarten", () => {
  const card = buildCard();
  card._carePlant = "p1";
  card._data.pflanzen = [{
    id: "p1", name: "Hasel", wissenschaftlich: "Corylus avellana",
  }];
  assert.equal(card._eiveHTML(), "");
  card._eive = {profile: {
    p1: {wissenschaftlich: "Corylus maxima", indikatoren: {
      L: {wert: 4.1, quellsysteme: 5},
    }},
  }};
  assert.equal(card._eiveHTML(), "");
  card._eive.profile.p1.wissenschaftlich = "Corylus avellana";
  card._eive.profile.p1.indikatoren.L.wert = -1;
  assert.equal(card._eiveHTML(), "");
});

test("EIVE-Daten werden HTML-sicher gerendert", () => {
  const card = buildCard();
  const species = 'Corylus <img src=x onerror=alert(1)>';
  card._carePlant = "p1";
  card._data.pflanzen = [{id: "p1", name: "Testpflanze", wissenschaftlich: species}];
  card._eive = {profile: {p1: {
    wissenschaftlich: species,
    indikatoren: {L: {wert: 8.4, quellsysteme: 2}},
  }}};
  const html = card._eiveHTML();
  assert.ok(html.includes("&lt;img"));
  assert.ok(!html.includes('<img src=x onerror'));
  assert.ok(html.includes('CC BY 4.0'));
});


test("Pflegeverlauf trennt echte Gießvorgänge von Kontrollen ohne Wasser", () => {
  const card = buildCard();
  card._data.pflanzen = [
    { id: "p1", name: "Lavendel", wissenschaftlich: "Lavandula angustifolia" },
    { id: "p2", name: "Hortensie", wissenschaftlich: "Hydrangea macrophylla" },
  ];
  card._data.aufgaben = [
    { id: "a1", pflanzen_id: "p1", name: "Gießbedarf prüfen",
      status: "erledigt", aufgabentyp: "giesskontrolle",
      ergebnis: "gegossen", erledigt_utc: "2026-10-20T12:00:00+00:00",
      faellig_am: "2026-10-20" },
    { id: "a2", pflanzen_id: "p1", name: "Gießbedarf prüfen",
      status: "erledigt", aufgabentyp: "giesskontrolle",
      ergebnis: "kontrolliert_kein_wasser", erledigt_utc: "2026-10-29T11:00:00+00:00",
      faellig_am: "2026-10-29" },
    { id: "a3", pflanzen_id: "p1", name: "Boden prüfen",
      status: "erledigt", aufgabentyp: "einfach",
      ergebnis: "erledigt", erledigt_utc: "2026-10-25T13:00:00+00:00" },
    { id: "a4", pflanzen_id: "p1", name: "Wieder geöffnet",
      status: "offen", aufgabentyp: "giesskontrolle",
      ergebnis: null, erledigt_utc: null },
    { id: "a5", pflanzen_id: "p2", name: "Gießen",
      status: "erledigt", aufgabentyp: "giesskontrolle",
      ergebnis: "gegossen", erledigt_utc: "2026-10-30T14:00:00+00:00" },
  ];
  card._data.historie = [
    { art: "aufgabe_erledigt", objekt_id: "a1", person: "Gärtnerin" },
    { art: "aufgabe_erledigt", objekt_id: "a2", person: "Gärtner" },
    { art: "aufgabe_wieder_geoeffnet", objekt_id: "a4", person: "Andere Person" },
  ];
  const info = card._pflegeverlaufDaten("p1");
  assert.equal(info.erledigt.length, 3);
  assert.equal(info.giesskontrollen, 2);
  assert.equal(info.gegossen, 1);
  assert.equal(info.keinWasser, 1);
  assert.equal(info.letzteKontrolle.id, "a2");
  assert.equal(info.zuletztGegossen.id, "a1");
  assert.deepEqual(Array.from(info.erledigt.map((x) => x.id)), ["a2", "a3", "a1"]);
  card._onClick({ target: { closest: () => ({
    disabled: false, dataset: { action: "pflegeverlauf-open", id: "p1" },
  }) }});
  assert.equal(card._modal.type, "pflegeverlauf");
  const html = card._pflegeverlaufHTML();
  assert.ok(card._modalHTML().includes("Pflegeverlauf: Lavendel"));
  assert.ok(html.includes("Zuletzt tatsächlich gegossen"));
  assert.ok(html.includes("Letzte Gießkontrolle"));
  assert.ok(html.includes("Kontrolliert – kein Wasser nötig"));
  assert.ok(html.includes("Gärtnerin"));
  assert.ok(html.includes("Gärtner"));
  assert.ok(!html.includes("Wieder geöffnet"));
  assert.ok(!html.includes("Andere Person"));
  assert.ok(!html.includes("Hortensie"));
  assert.ok(html.includes("Eine Gießkontrolle ohne Wasser zählt nicht als Gießen"));
  assert.ok(!html.includes('data-action="task-done"'));
});

test("Pflanzenkarte zeigt letzte dokumentierte Gießkontrolle, keine fremden Pflanzen", () => {
  const card = buildCard();
  card._data.pflanzen = [
    { id: "p1", name: "Lavendel", gruppe: "Gemüse und Kräuter", bereich_id: null },
    { id: "p2", name: "Hortensie", gruppe: "Blumen, Stauden und Rosen", bereich_id: null },
  ];
  card._data.aufgaben = [
    { id: "k1", pflanzen_id: "p1", name: "Gießkontrolle",
      status: "erledigt", aufgabentyp: "giesskontrolle",
      ergebnis: "kontrolliert_kein_wasser", erledigt_utc: "2026-10-30T12:34:00+00:00" },
    { id: "k2", pflanzen_id: "p2", name: "Gießkontrolle",
      status: "erledigt", aufgabentyp: "giesskontrolle",
      ergebnis: "gegossen", erledigt_utc: "2026-10-29T12:34:00+00:00" },
  ];
  const html = card._plantsHTML();
  assert.ok(html.includes("Letzte Gießkontrolle:"));
  assert.ok(html.includes("Kein Wasser nötig"));
  assert.ok(html.includes("Gegossen"));
  assert.ok(html.includes('data-action="pflegeverlauf-open" data-id="p1"'));
  assert.ok(html.includes('data-action="pflegeverlauf-open" data-id="p2"'));
  assert.ok(html.includes("30.10.2026"));
});

test("Pflegeverlauf zeigt keine gelöschten, fremden oder wieder geöffneten Arbeiten", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Rose", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._data.aufgaben = [{
    id: "a1", pflanzen_id: "p1", name: "Wieder geöffnet",
    status: "offen", ergebnis: null,
  }, {
    id: "a2", pflanzen_id: "p2", name: "Gießarbeit einer anderen Pflanze",
    status: "erledigt", ergebnis: "gegossen", aufgabentyp: "giesskontrolle",
  }];
  card._data.historie = [{
    objekt_id: "a-deleted", art: "aufgabe_erledigt",
    person: "Vertrauliche historische Person",
  }];
  card._modal = { type: "pflegeverlauf", existing: plant };
  const html = card._pflegeverlaufHTML();
  assert.ok(html.includes("Noch keine Gießkontrolle dokumentiert"));
  assert.ok(html.includes("Noch kein tatsächliches Gießen dokumentiert"));
  assert.ok(html.includes("noch keine Pflegearbeiten"));
  assert.ok(!html.includes("Wieder geöffnet"));
  assert.ok(!html.includes("andere Pflanze"));
  assert.ok(!html.includes("Vertrauliche"));
});

test("Pflegeverlauf blättert ohne Datenverlust in Schritten von 20", () => {
  const card = buildCard();
  card._data.pflanzen = [{ id: "p1", name: "Rose" }];
  card._data.aufgaben = Array.from({ length: 23 }, (_, i) => ({
    id: "h" + i, pflanzen_id: "p1", name: "Pflegeeintrag " + i,
    status: "erledigt", ergebnis: "erledigt",
    erledigt_utc: "2026-10-" + String(i + 1).padStart(2, "0") + "T10:00:00+00:00",
  }));
  card._onClick({ target: { closest: () => ({
    disabled: false, dataset: { action: "pflegeverlauf-open", id: "p1" },
  }) }});
  let html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Pflegeeintrag 22"));
  assert.ok(!html.includes("Pflegeeintrag 0</div>"));
  assert.ok(html.includes("3 verbleibend"));
  card._onClick({ target: { closest: () => ({
    disabled: false, dataset: { action: "pflegeverlauf-mehr", id: "p1" },
  }) }});
  html = card.shadowRoot.innerHTML;
  assert.ok(html.includes("Pflegeeintrag 0"));
  assert.ok(!html.includes("verbleibend"));
  assert.equal(card._verlaufLimit, 40);
});

test("Pflegeverlauf escaped Namen und Personalangaben und erkennt ungültige Zeitpunkte", () => {
  const card = buildCard();
  const plant = { id: "p1", name: "Pflanze <script>", wissenschaftlich: "Rosa canina" };
  card._data.pflanzen = [plant];
  card._data.aufgaben = [{
    id: "a1", pflanzen_id: "p1",
    name: '<img src=x onerror=alert(1)>',
    status: "erledigt", ergebnis: "gegossen",
    aufgabentyp: "giesskontrolle",
    erledigt_utc: "<img src=x onerror=alert(1)>",
  }];
  card._data.historie = [{
    objekt_id: "a1", art: "aufgabe_erledigt", person: "<script>privat</script>",
  }];
  card._modal = { type: "pflegeverlauf", existing: plant };
  const html = card._modalHTML();
  for (const expected of [
    "&lt;script&gt;", "&lt;img src=x onerror=alert(1)&gt;",
    "Zeitpunkt nicht gespeichert", "&lt;script&gt;privat&lt;/script&gt;",
  ]) assert.ok(html.includes(expected), expected);
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes("<img src=x"));
});

test("Pflegeverlauf ignoriert manipulierte Verlauf-Mehr-Klicks für andere Pflanzen", () => {
  const card = buildCard();
  card._data.pflanzen = [{ id: "p1", name: "Rose" }, { id: "p2", name: "Lavendel" }];
  card._modal = { type: "pflegeverlauf", existing: card._data.pflanzen[0] };
  card._verlaufLimit = 20;
  card._onClick({ target: { closest: () => ({
    disabled: false, dataset: { action: "pflegeverlauf-mehr", id: "p2" },
  }) }});
  assert.equal(card._verlaufLimit, 20);
  assert.equal(card._modal.existing.id, "p1");
});
