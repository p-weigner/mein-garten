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
