/* Mein Garten V1 – eigenständige Lovelace-Karte, ohne Bibliotheken.
   Backend: custom_components/mein_garten (WebSocket).
   Beta: keine automatische fachliche Freigabe von Pflegeaufgaben.
*/
(() => {
  "use strict";

  const ESC = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  };
  const escapeHtml = (value) => String(value == null ? "" : value).replace(/[&<>"']/g, (c) => ESC[c]);
  const dateLabel = (date) => {
    if (!date) return "Ohne Termin";
    const [year, month, day] = String(date).split("-");
    return day && month && year ? day + "." + month + "." + year : String(date);
  };
  const dateToday = () => {
    const d = new Date();
    const year = d.getFullYear();
    return year + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  };
  const byDate = (a, b) => (a.faellig_am || "9999-99-99").localeCompare(b.faellig_am || "9999-99-99");
  const CSS = [
    ":host{display:block;--garten-bg:#15231b;--garten-card:#203329;--garten-card2:#263c2e;--garten-border:#3c5946;--garten-text:#eaf2e8;--garten-muted:#a6bca9;--garten-accent:#b0d0a8;--garten-shadow:0 14px 34px #08150c50}",
    "*{box-sizing:border-box}button,input,select,textarea{font:inherit}button{cursor:pointer}button:disabled{opacity:.5;cursor:default}",
    ".garden{background:linear-gradient(125deg,#17261d,#14211a 68%,#1b3222);color:var(--garten-text);min-height:calc(100vh - 80px);padding:24px max(18px,calc((100% - 1180px)/2));font:400 14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}",
    ".hero{display:flex;align-items:center;justify-content:space-between;gap:20px;margin:0 0 22px;flex-wrap:wrap}.eyebrow{font-weight:700;color:var(--garten-accent);letter-spacing:.14em;font-size:11px;text-transform:uppercase}.hero h1{font-size:clamp(26px,4vw,40px);line-height:1.17;margin:4px 0 3px;letter-spacing:-.035em}.sub{color:var(--garten-muted);font-size:13px}.hero-icon{font-size:38px;padding:13px;background:#2b4c32;border:1px solid #55775c;border-radius:20px}",
    ".tabs{display:flex;gap:6px;padding:6px;background:#203228;border:1px solid var(--garten-border);border-radius:16px;overflow-x:auto;margin-bottom:24px}.tab{border:0;background:transparent;color:var(--garten-muted);padding:12px 20px;min-width:105px;border-radius:11px;font-weight:600;transition:.18s}.tab:hover{background:#314839;color:var(--garten-text)}.tab[aria-selected=true]{background:#42664a;color:#f2fff0;box-shadow:inset 0 0 0 1px #60896b}",
    ".heading{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:16px}.heading h2{margin:0;font-size:21px;font-weight:650;letter-spacing:-.025em}",
    ".btn{border:1px solid var(--garten-border);border-radius:12px;background:#2b4435;color:var(--garten-text);padding:9px 14px;font-weight:650;transition:.15s}.btn:hover{background:#3b5944;border-color:#779b7f}.btn.primary{background:#91b68c;color:#102315;border-color:#b1d5ad}.btn.primary:hover{background:#acd2a7}.btn.ghost{background:transparent}.btn.danger{color:#f5b2b1}.btn.tiny{padding:6px 10px;font-size:12px}.buttons{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-bottom:25px}",
    ".card,.stat{background:var(--garten-card);border:1px solid var(--garten-border);border-radius:18px;padding:19px;box-shadow:var(--garten-shadow)}.stat .count{font-size:32px;font-weight:750;color:var(--garten-accent);line-height:1.25}.stat .label{color:var(--garten-muted);font-size:12px}.card h3{font-size:17px;margin:0 0 8px;letter-spacing:-.018em}.card p{margin:0 0 10px;color:var(--garten-muted)}.card .footer{margin-top:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}",
    ".chip{display:inline-block;border:1px solid #5a765f;border-radius:999px;color:#d0e0cc;font-size:11px;padding:2px 9px;background:#2b4633}.chip.muted{color:var(--garten-muted);border-color:var(--garten-border);background:transparent}.chip.warning{color:#f0d49b;border-color:#806f45;background:#433b24}.line{border:0;border-top:1px solid var(--garten-border);margin:16px 0}",
    ".empty{padding:30px 20px;text-align:center;border:1px dashed #58745c;border-radius:18px;color:var(--garten-muted);background:#21352a}.empty .symbol{font-size:32px;margin-bottom:8px}",
    ".task{display:flex;align-items:center;justify-content:space-between;gap:12px;border-bottom:1px solid #3a5643;padding:12px 0}.task:last-child{border-bottom:0}.task-name{font-weight:600}.task-meta{font-size:12px;color:var(--garten-muted)}.task.done .task-name{text-decoration:line-through;opacity:.7}.tag{font-size:11px;color:#e1c995}",
    ".section{margin-bottom:24px}.section-title{margin:19px 0 11px;font-size:13px;font-weight:750;letter-spacing:.09em;text-transform:uppercase;color:var(--garten-accent)}",
    ".notice{border-left:3px solid #91b68c;background:#253a2b;border-radius:0 10px 10px 0;padding:11px 14px;color:var(--garten-muted);margin:12px 0 18px}",
    ".error{padding:10px 13px;border:1px solid #bd7873;background:#55362f;color:#ffe3dd;border-radius:12px;margin:0 0 16px}",
    ".modal-backdrop{position:fixed;inset:0;z-index:1000;background:#020804aa;display:flex;justify-content:center;align-items:center;padding:18px}",
    ".dialog{width:min(620px,100%);max-height:min(85vh,900px);overflow-y:auto;background:#1d3025;border:1px solid #67846a;border-radius:22px;padding:24px;box-shadow:0 22px 90px #0009;color:var(--garten-text)}.dialog h2{margin:0 0 17px;font-size:22px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.field{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}.field.full{grid-column:1/-1}",
    ".field label{font-size:12px;color:var(--garten-muted);font-weight:700}.field input,.field select,.field textarea{width:100%;padding:11px 12px;outline:none;background:#17271e;border:1px solid #4c6952;border-radius:11px;color:var(--garten-text);min-height:42px}.field textarea{min-height:82px;resize:vertical}.field input:focus,.field select:focus,.field textarea:focus{border-color:#b2d6aa;box-shadow:0 0 0 2px #82b47c30}",
    ".field.check-field label{display:flex;align-items:center;gap:10px;flex-direction:row;font-weight:600}.field.check-field input[type=checkbox]{width:18px;height:18px;min-height:18px;flex:none;margin:0;accent-color:#91b68c}",
    ".dialog-foot{display:flex;gap:9px;justify-content:flex-end;margin-top:13px;flex-wrap:wrap}.suggestions{max-height:185px;overflow-y:auto;border:1px solid var(--garten-border);background:#17271e;border-radius:11px;margin-bottom:15px}.suggestion{display:flex;align-items:center;justify-content:space-between;gap:9px;padding:9px 12px;width:100%;text-align:left;border:0;border-bottom:1px solid #344b39;background:transparent;color:var(--garten-text)}.suggestion:hover{background:#2d4634}.suggestion:last-child{border-bottom:0}.small{font-size:12px;color:var(--garten-muted)}",
    "@media(max-width:700px){.garden{padding:15px}.hero-icon{display:none}.stats{grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}.stat{padding:13px}.stat .count{font-size:25px}.tabs{gap:2px}.tab{padding:11px 8px;min-width:78px;font-size:12px}.grid{grid-template-columns:1fr}.dialog{padding:17px}.form-grid{grid-template-columns:1fr}}",
    "@media(prefers-reduced-motion:reduce){*{transition:none!important}}"
  ].join("\n");

  class MeinGartenCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
      this._tab = "start";
      this._data = null;
      this._groups = [];
      this._automatik = null;
      this._saison = null;
      this._modal = null;
      this._query = "";
      this._suggestions = [];
      this._searchMessage = "";
      this._searchGeneration = 0;
      this._care = null;
      this._careLoading = false;
      this._carePlant = null;
      this._working = false;
      this._error = "";
      this._connection = null;
      this._unsubscribe = null;
      this._subscribing = false;
      this._connected = false;
      this._onClick = this._onClick.bind(this);
      this._onSubmit = this._onSubmit.bind(this);
      this._onInput = this._onInput.bind(this);
      this._onKeydown = this._onKeydown.bind(this);
      this.shadowRoot.addEventListener("click", this._onClick);
      this.shadowRoot.addEventListener("submit", this._onSubmit);
      this.shadowRoot.addEventListener("input", this._onInput);
      this.shadowRoot.addEventListener("keydown", this._onKeydown);
    }

    setConfig(config) {
      this._config = config || {};
      this._render();
    }

    getCardSize() { return 10; }

    set hass(value) {
      const changed = !this._connection || this._connection !== value.connection;
      this._hass = value;
      if (changed && this._connected) this._connect();
    }

    connectedCallback() {
      this._connected = true;
      this._render();
      if (this._hass) this._connect();
    }

    disconnectedCallback() {
      this._connected = false;
      this._connection = null;
      clearTimeout(this._searchTimer);
      this._searchGeneration++;
      if (this._unsubscribe) {
        this._unsubscribe();
        this._unsubscribe = null;
      }
    }

    async _connect() {
      const connection = this._hass && this._hass.connection;
      if (!connection || (this._connection === connection && (this._unsubscribe || this._subscribing))) return;
      if (this._unsubscribe) this._unsubscribe();
      this._unsubscribe = null;
      this._connection = connection;
      this._subscribing = true;
      try {
        const unsubscribe = await connection.subscribeMessage(
          (event) => {
            if (this._connected && this._connection === connection) {
              this._data = event.daten;
              this._groups = event.gruppen || [];
              this._automatik = event.automatik || null;
              this._saison = event.saison || null;
              this._error = "";
              this._render();
            }
          },
          { type: "mein_garten/subscribe" }
        );
        if (!this._connected || this._connection !== connection) {
          unsubscribe();
          return;
        }
        this._unsubscribe = unsubscribe;
      } catch (err) {
        this._error = this._errorText(err, "Backend nicht erreichbar");
        this._render();
      } finally {
        this._subscribing = false;
      }
    }

    _errorText(err, fallback) {
      return err && (err.message || err.code)
        ? String(err.message || err.code)
        : fallback;
    }

    async _call(type, args) {
      if (!this._hass) throw new Error("Home Assistant ist nicht verbunden");
      return this._hass.callWS(Object.assign({ type: "mein_garten/" + type }, args || {}));
    }

    async _mutate(type, args) {
      if (this._working) return;
      this._working = true;
      this._error = "";
      try {
        const result = await this._call(type, args);
        if (result && result.daten) {
          this._data = result.daten;
          this._groups = result.gruppen || [];
          this._automatik = result.automatik || null;
          this._saison = result.saison || null;
        }
        this._modal = null;
        this._render();
      } catch (err) {
        this._error = this._errorText(err, "Die Änderung konnte nicht gespeichert werden");
        this._render();
      } finally {
        this._working = false;
      }
    }

    _onKeydown(ev) {
      if (ev.key === "Escape" && this._modal) {
        ev.preventDefault();
        this._modal = null;
        this._render();
      }
    }

    _onInput(ev) {
      const target = ev.target;
      if (target && target.dataset && target.dataset.role === "plant-search") {
        this._query = target.value;
        this._searchGeneration++;
        clearTimeout(this._searchTimer);
        this._suggestions = [];
        this._searchMessage = this._query.trim().length >= 2
          ? "Suche nach passenden Pflanzen …"
          : "Mindestens zwei Zeichen eingeben.";
        this._renderSuggestions();
        if (this._query.trim().length >= 2) {
          const generation = this._searchGeneration;
          this._searchTimer = setTimeout(() => this._search(generation), 450);
        }
      }
    }

    async _search(generation) {
      const query = this._query.trim();
      if (query.length < 2) return;
      try {
        const result = await this._call("pflanzen_suchen", { suchbegriff: query });
        if (generation !== this._searchGeneration || !this._modal) return;
        this._suggestions = result.pflanzen || [];
        this._searchMessage = this._suggestions.length
          ? ""
          : "Keine passende Art gefunden. Du kannst die Pflanze trotzdem manuell anlegen.";
        if (result.quellenstatus && result.quellenstatus.length) {
          this._searchMessage += (this._searchMessage ? " " : "") +
            "Hinweis: " + result.quellenstatus.join(", ") + ".";
        }
      } catch (err) {
        if (generation !== this._searchGeneration) return;
        this._suggestions = [];
        this._searchMessage = this._errorText(err, "Pflanzensuche derzeit nicht verfügbar");
      }
      this._renderSuggestions();
    }

    _renderSuggestions() {
      const el = this.shadowRoot.querySelector("#garten-vorschlaege");
      if (el) el.innerHTML = this._suggestionHTML();
    }

    _suggestionHTML() {
      if (!this._suggestions.length) {
        return '<div class="small" style="padding:11px">' +
          escapeHtml(this._searchMessage || "Suche einen deutschen oder botanischen Namen.") +
          "</div>";
      }
      return this._suggestions.map((plant, index) => {
        const alternativeSchreibweise =
          (plant.quellen || []).includes("Schreibvariante");
        const mehrdeutigerName = alternativeSchreibweise ||
          (!plant.deutsch && (plant.quellen || []).includes("GBIF-Trivialnamen"));
        return '<button type="button" class="suggestion" data-action="suggestion" data-index="' +
          index + '"><span><strong>' +
          escapeHtml(plant.deutsch || plant.wissenschaftlich) +
          '</strong><span class="small" style="display:block">' +
          escapeHtml(plant.wissenschaftlich) +
          '</span></span><span class="chip ' +
          (plant.bestaetigt && !mehrdeutigerName ? '' : 'warning') + '">' +
          (alternativeSchreibweise ? "Namensvariante – Art prüfen" :
            mehrdeutigerName ? "Trivialname – Art prüfen" :
            plant.bestaetigt ? "Art bestätigt" : "Bitte Art prüfen") +
          "</span></button>";
      }).join("");
    }

    _onClick(ev) {
      const btn = ev.target.closest("[data-action]");
      if (!btn || btn.disabled) return;
      const action = btn.dataset.action;
      const id = btn.dataset.id || "";
      if (action === "tab") {
        this._tab = btn.dataset.tab || "start";
        this._modal = null;
        this._render();
      } else if (action === "close") {
        this._modal = null;
        this._render();
      } else if (action === "plant-new" || action === "plant-edit") {
        const existing = action === "plant-edit" ? this._getPlant(id) : null;
        this._modal = { type: "pflanze", existing };
        this._suggestions = [];
        this._searchMessage = "";
        this._query = "";
        this._render();
      } else if (action === "care-plan") {
        const plant = this._getPlant(id);
        const key = btn.dataset.field || "";
        const field = this._care?.felder?.[key];
        if (!plant || !field || !field.text) return;
        const titel = {
          watering: "Gießbedarf prüfen",
          sunlight: "Standort prüfen",
          soil: "Boden prüfen",
          pruning: "Schnittbedarf prüfen",
          fertilization: "Düngebedarf prüfen",
        }[key];
        if (!titel) return;
        this._modal = {
          type: "regel",
          prefill: {
            name: titel + " – " + plant.name,
            pflanzen_id: plant.id,
            bereich_id: plant.bereich_id,
            rhythmus: "jaehrlich",
            pflegefeld: key,
            aufgabentyp: key === "watering" ? "giesskontrolle" : "einfach",
          },
          careInfo: "Dieser Termin wird von dir festgelegt. Die Quelle " +
            "OpenPlantbook und ihre Übersetzung sind nicht fachlich geprüft.",
        };
        this._render();
      } else if (action === "care-open") {
        const plant = this._getPlant(id);
        if (!plant) return;
        this._modal = { type: "pflege", existing: plant };
        this._care = null;
        this._carePlant = id;
        this._careLoading = true;
        this._render();
        this._loadCare(id);
      } else if (action === "area-new") {
        this._modal = { type: "bereich" };
        this._render();
      } else if (action === "saisonanker-open") {
        this._modal = { type: "saisonanker" };
        this._render();
      } else if (action === "saison-plan") {
        const hit = (this._saison?.vorschlaege || []).find((r) =>
          r.pflanzen_id === id && r.katalog_id === btn.dataset.katalog);
        if (!hit || hit.vorgemerkt || !hit.fenster_von || !hit.fenster_bis) return;
        this._modal = { type: "saison", eintrag: hit };
        this._render();
      } else if (action === "automatik-open") {
        this._modal = { type: "automatik" };
        this._render();
      } else if (action === "rule-new") {
        this._modal = { type: "regel" };
        this._render();
      } else if (action === "rule-toggle" || action === "rule-remove") {
        const rule = (this._data.regeln || []).find((r) => r.id === id);
        if (!rule) return;
        if (action === "rule-remove" && !window.confirm("Diese Wiederholung entfernen? Erledigte Aufgaben bleiben erhalten.")) return;
        this._mutate(action === "rule-remove" ? "regel_entfernen" : "regel_aktiv_setzen",
          action === "rule-remove" ? { regel_id: id } : { regel_id: id, aktiv: !rule.aktiv });
      } else if (action === "task-new") {
        this._modal = { type: "aufgabe" };
        this._render();
      } else if (action === "task-result") {
        const task = (this._data.aufgaben || []).find((t) => t.id === id);
        if (!task || task.status !== "offen" || task.aufgabentyp !== "giesskontrolle") return;
        this._modal = { type: "giessen", existing: task };
        this._render();
      } else if (action === "task-water-choice") {
        const task = this._modal && this._modal.type === "giessen" && this._modal.existing;
        if (!task || task.id !== id || task.status !== "offen") return;
        const ergebnis = btn.dataset.result;
        if (!["gegossen", "kontrolliert_kein_wasser"].includes(ergebnis)) return;
        this._mutate("aufgabe_erledigen", { aufgaben_id: id, ergebnis });
      } else if (action === "suggestion") {
        const candidate = this._suggestions[Number(btn.dataset.index)];
        if (!candidate) return;
        const form = this.shadowRoot.querySelector('form[data-form="pflanze"]');
        if (!form) return;
        form.elements.namedItem("wissenschaftlich").value = candidate.wissenschaftlich;
        const name = form.elements.namedItem("name");
        if (!name.value.trim()) name.value = candidate.deutsch || candidate.wissenschaftlich;
        const note = this.shadowRoot.querySelector("#garten-artenhinweis");
        const quellen = candidate.quellen || [];
        const istVariante = quellen.includes("Schreibvariante");
        const aliasMehrdeutig = istVariante ||
          (!candidate.deutsch && quellen.includes("GBIF-Trivialnamen"));
        if (note) note.textContent = aliasMehrdeutig
          ? "Botanisches Taxon bestätigt. Die Zuordnung einer alternativen Schreibweise oder eines deutschen Sammelnamens ist nicht eindeutig: bitte die tatsächliche Art prüfen."
          : candidate.bestaetigt
            ? "Botanische Art bestätigt: " + candidate.wissenschaftlich
            : "Die Zuordnung ist noch nicht bestätigt. Für diese Pflanze werden keine artspezifischen Pflegemaßnahmen abgeleitet.";
      } else if (action === "plant-remove" || action === "area-remove" || action === "task-remove") {
        const question = action === "plant-remove"
          ? "Diese Pflanze und ihre verknüpften Aufgaben wirklich entfernen?"
          : action === "area-remove"
            ? "Diesen Bereich entfernen? Die Pflanzen bleiben ohne Bereich erhalten."
            : "Diese Aufgabe wirklich löschen?";
        if (!window.confirm(question)) return;
        const type = action === "plant-remove" ? "pflanze_entfernen"
          : action === "area-remove" ? "bereich_entfernen" : "aufgabe_entfernen";
        const key = action === "plant-remove" ? "pflanzen_id"
          : action === "area-remove" ? "bereich_id" : "aufgaben_id";
        this._mutate(type, { [key]: id });
      } else if (action === "area-rename") {
        const area = this._getArea(id);
        if (!area) return;
        const name = window.prompt("Neuer Name für den Gartenbereich:", area.name);
        if (name === null || !name.trim()) return;
        this._mutate("bereich_umbenennen", { bereich_id: id, name: name.trim() });
      } else if (action === "task-done" || action === "task-reopen") {
        this._mutate(
          action === "task-done" ? "aufgabe_erledigen" : "aufgabe_wieder_oeffnen",
          { aufgaben_id: id }
        );
      }
    }

    async _loadCare(id) {
      try {
        const result = await this._call("pflegeprofil", { pflanzen_id: id });
        if (this._carePlant !== id || !this._modal || this._modal.type !== "pflege") return;
        this._care = result;
      } catch (err) {
        if (this._carePlant !== id || !this._modal || this._modal.type !== "pflege") return;
        this._care = { status: "fehler", meldung: this._errorText(err, "Pflegeprofil nicht verfügbar") };
      } finally {
        if (this._carePlant === id && this._modal && this._modal.type === "pflege") {
          this._careLoading = false;
          this._render();
        }
      }
    }

    _careHTML() {
      if (this._careLoading) return '<p class="small">Deutsche Pflegeinformationen werden geladen …</p>';
      const profile = this._care;
      if (!profile) return '<p class="small">Kein Pflegeprofil verfügbar.</p>';
      const labels = {
        quelle_nicht_eingerichtet: "OpenPlantbook ist nicht eingerichtet.",
        quelle_nicht_erreichbar: "OpenPlantbook ist momentan nicht erreichbar.",
        art_nicht_gefunden: "Für diese botanische Art sind noch keine Pflegeinformationen vorhanden.",
        art_nicht_bestaetigt: "Die botanische Art konnte nicht eindeutig bestätigt werden.",
        art_unbekannt: "Bitte zuerst einen gültigen botanischen Artnamen auswählen.",
        kein_deutscher_text: "Noch keine deutsche Übersetzung verfügbar. Die Suche wird erneut versucht.",
        teilweise: "Einige Pflegefelder sind noch nicht übersetzt und werden später automatisch erneut geprüft.",
        quellenantwort_ungueltig: "Unerwartete Antwort der Pflegequelle.",
        fehler: "Pflegeprofil konnte nicht geladen werden."
      };
      const heading = '<div class="notice">Quelle: <a href="https://open.plantbook.io/" target="_blank" rel="noopener noreferrer">OpenPlantbook</a> · Automatisch übersetzt, nicht fachlich geprüft. Daraus werden keine automatischen Pflegeaufgaben erzeugt.</div>';
      const fields = Object.entries(profile.felder || {});
      const body = fields.map(([key, f]) => '<section class="card" style="margin:9px 0;padding:13px"><h3>' +
        escapeHtml(f.titel) + '</h3><p style="white-space:pre-wrap">' +
        escapeHtml(f.text || (f.status === "uebersetzung_ausstehend" ?
          "Übersetzung ausstehend; keine erfundenen Angaben." : "Keine Angabe verfügbar.")) +
        '</p>' + (f.text && this._carePlant ?
          '<button type="button" class="btn tiny" data-action="care-plan" data-id="' +
          escapeHtml(this._carePlant) + '" data-field="' + escapeHtml(key) +
          '">Jährliche Kontrolle dazu planen</button>' : '') +
        '</section>').join("");
      return (profile.status !== "ok" ? '<p class="small">' +
        escapeHtml(profile.meldung || labels[profile.status] || "Keine Angaben verfügbar.") +
        '</p>' : "") + heading + body;
    }

    _getPlant(id) {
      return (this._data && this._data.pflanzen || []).find((p) => p.id === id);
    }

    _getArea(id) {
      return (this._data && this._data.bereiche || []).find((a) => a.id === id);
    }

    _onSubmit(ev) {
      const form = ev.target;
      if (!form || !form.dataset || !form.dataset.form) return;
      ev.preventDefault();
      const val = (key) => (form.elements.namedItem(key)?.value || "").trim();
      if (form.dataset.form === "pflanze") {
        const data = {
          name: val("name"),
          wissenschaftlich: val("wissenschaftlich"),
          notizen: val("notizen"),
          gruppe: val("gruppe") || null,
          bereich_id: val("bereich_id") || null,
        };
        if (this._modal && this._modal.existing) {
          data.pflanzen_id = this._modal.existing.id;
          this._mutate("pflanze_bearbeiten", data);
        } else {
          this._mutate("pflanze_anlegen", data);
        }
      } else if (form.dataset.form === "bereich") {
        this._mutate("bereich_anlegen", { name: val("name") });
      } else if (form.dataset.form === "saisonanker") {
        this._mutate("saisonanker_speichern", {
          last_frost: val("last_frost"),
          first_frost: val("first_frost"),
        });
      } else if (form.dataset.form === "saison") {
        const item = this._modal?.eintrag;
        if (!item || this._modal.type !== "saison") return;
        this._mutate("saison_vormerken", {
          pflanzen_id: item.pflanzen_id,
          katalog_id: item.katalog_id,
          datum: val("datum"),
        });
      } else if (form.dataset.form === "automatik") {
        const isChecked = (key) => form.elements.namedItem(key).checked;
        this._mutate("automatik_speichern", {
          weather_entity: val("weather_entity"),
          notify_target: val("notify_target"),
          freitag_aktiv: isChecked("freitag_aktiv"),
          frost_aktiv: isChecked("frost_aktiv"),
          frost_grenze_c: Number(val("frost_grenze_c")),
        });
      } else if (form.dataset.form === "regel") {
        this._mutate("regel_anlegen", {
          name: val("name"), startdatum: val("startdatum"), rhythmus: val("rhythmus"),
          intervall_tage: val("rhythmus") === "tage" ? Number(val("intervall_tage")) : null,
          pflanzen_id: val("pflanzen_id") || null,
          bereich_id: val("bereich_id") || null,
          pflegefeld: this._modal?.prefill?.pflegefeld || null,
          aufgabentyp: val("aufgabentyp") || "einfach",
        });
      } else if (form.dataset.form === "aufgabe") {
        this._mutate("aufgabe_anlegen", {
          name: val("name"),
          faellig_am: val("faellig_am") || null,
          pflanzen_id: val("pflanzen_id") || null,
          bereich_id: val("bereich_id") || null,
          aufgabentyp: val("aufgabentyp") || "einfach",
        });
      }
    }

    _options(items, selected, includeEmpty) {
      let result = includeEmpty ? '<option value="">Nicht zugeordnet</option>' : "";
      return result + items.map((item) =>
        '<option value="' + escapeHtml(item.value) + '"' +
        (item.value === selected ? " selected" : "") + ">" +
        escapeHtml(item.label) + "</option>"
      ).join("");
    }

    _plantForm() {
      const p = this._modal.existing || {};
      const groups = this._groups.map((g) => ({ value: g, label: g }));
      const areas = (this._data.bereiche || []).map((a) => ({
        value: a.id, label: a.name
      }));
      return '<form data-form="pflanze"><div class="form-grid">' +
        '<div class="field full"><label for="garten-suche">Pflanzenart suchen (optional)</label>' +
        '<input id="garten-suche" type="search" autocomplete="off" data-role="plant-search" placeholder="z. B. Bauernhortensie, Lavendel, Tomate">' +
        '<div class="small">Deutsche und botanische Namen; passende Art auswählen.</div>' +
        '<div id="garten-vorschlaege" class="suggestions">' + this._suggestionHTML() + '</div>' +
        '<div id="garten-artenhinweis" class="small">Eine unbekannte Pflanze kann auch ohne Suchtreffer angelegt werden.</div></div>' +
        '<div class="field"><label for="garten-name">Eigener Pflanzenname *</label>' +
        '<input id="garten-name" name="name" required maxlength="120" value="' +
        escapeHtml(p.name || "") + '" placeholder="z. B. Meine Hortensie"></div>' +
        '<div class="field"><label for="garten-latin">Wissenschaftlicher Name</label>' +
        '<input id="garten-latin" name="wissenschaftlich" maxlength="160" value="' +
        escapeHtml(p.wissenschaftlich || "") + '" placeholder="Hydrangea macrophylla"></div>' +
        '<div class="field"><label for="garten-gruppe">Pflanzengruppe</label>' +
        '<select id="garten-gruppe" name="gruppe">' +
        this._options(groups, p.gruppe, true) + '</select></div>' +
        '<div class="field"><label for="garten-bereich">Gartenbereich</label>' +
        '<select id="garten-bereich" name="bereich_id">' +
        this._options(areas, p.bereich_id, true) + '</select></div>' +
        '<div class="field full"><label for="garten-notizen">Eigene Notizen</label>' +
        '<textarea id="garten-notizen" name="notizen" maxlength="4000" placeholder="Eigene Beobachtungen und Hinweise">' +
        escapeHtml(p.notizen || "") + '</textarea></div></div>' +
        '<div class="dialog-foot"><button type="button" data-action="close" class="btn ghost">Abbrechen</button>' +
        '<button type="submit" class="btn primary">' +
        (p.id ? "Änderungen speichern" : "Pflanze hinzufügen") +
        "</button></div></form>";
    }

    _saisonankerForm() {
      const a = this._saison?.anker || { last_frost: "", first_frost: "" };
      return '<form data-form="saisonanker"><div class="notice">' +
        'Die Vorhersage für einzelne Nächte ist kein zuverlässiger letzter Frostag. ' +
        'Trage für die gewünschte Gartensaison selbst geschätzte Referenztage ein. ' +
        'Eine US-Klimazone wird nicht auf deinen Garten übertragen.</div>' +
        '<div class="field"><label>Letzter erwarteter Frühjahrsfrost (optional)</label>' +
        '<input type="date" name="last_frost" min="2020-01-01" max="2100-12-31" value="' +
        escapeHtml(a.last_frost || "") + '"></div>' +
        '<div class="field"><label>Erster erwarteter Herbstfrost (optional)</label>' +
        '<input type="date" name="first_frost" min="2020-01-01" max="2100-12-31" value="' +
        escapeHtml(a.first_frost || "") + '"></div>' +
        '<div class="small">Nur Planungshilfen aus OpenPlantDB (CC0); ' +
        'es werden weder Aussaat noch Schnitt oder Düngung automatisch angeordnet. ' +
        'Für das nächste Gartenjahr müssen die Referenztage neu festgelegt werden.</div>' +
        '<div class="dialog-foot"><button type="button" class="btn ghost" data-action="close">Abbrechen</button>' +
        '<button type="submit" class="btn primary">Frost-Referenzdaten speichern</button></div></form>';
    }

    _saisonForm() {
      const r = this._modal.eintrag;
      return '<form data-form="saison"><div class="notice">' +
        'Unverbindlicher Aussaat-/Pflanzzeitraum aus US-Planungsdaten. ' +
        'Prüfe Art, Sorte, Standort und örtliche Witterung selbst. ' +
        'Es wird nur eine Erinnerungsaufgabe erzeugt, keine Aussaat ausgelöst.</div>' +
        '<p><strong>' + escapeHtml(r.pflanze) + '</strong> · <em>' +
        escapeHtml(r.wissenschaftlich) + '</em></p>' +
        '<p>' + escapeHtml(r.titel) + ' · ' +
        escapeHtml(dateLabel(r.fenster_von)) + ' – ' +
        escapeHtml(dateLabel(r.fenster_bis)) + '</p>' +
        '<div class="field"><label>Datum für deine Kontrollaufgabe *</label>' +
        '<input type="date" name="datum" required min="' +
        escapeHtml(r.fenster_von) + '" max="' + escapeHtml(r.fenster_bis) +
        '" value="' + escapeHtml(r.fenster_von) + '"></div>' +
        '<p class="small">Quelle: OpenPlantDB · CC0 1.0 · nicht regional fachlich geprüft</p>' +
        '<div class="dialog-foot"><button class="btn ghost" type="button" data-action="close">Abbrechen</button>' +
        '<button class="btn primary" type="submit">Als Kontrolle vormerken</button></div></form>';
    }

    _automatikForm() {
      const a = this._automatik || {
        weather_entity: "", notify_target: "", freitag_aktiv: false,
        frost_aktiv: false, frost_grenze_c: 2,
      };
      const weatherOptions = Object.keys(this._hass?.states || {})
        .filter((id) => /^weather\.[a-z0-9_]+$/.test(id)).sort();
      const notifyEntities = Object.keys(this._hass?.states || {})
        .filter((id) => /^notify\.[a-z0-9_]+$/.test(id));
      const notifyServices = Object.keys(this._hass?.services?.notify || {})
        .filter((id) => /^[a-z0-9_]+$/.test(id) && !["send_message", "notify"].includes(id))
        .map((id) => "notify." + id);
      const options = (items) => [...new Set(items)].sort().map((id) =>
        '<option value="' + escapeHtml(id) + '"></option>').join("");
      return '<form data-form="automatik"><div class="notice">' +
        'Beide Benachrichtigungen sind freiwillig und zunächst ausgeschaltet. ' +
        'Es wird ausschließlich die vorhandene Home-Assistant-Wettervorhersage genutzt; ' +
        'keine eigenen Pflanzennotizen werden versendet.</div>' +
        '<div class="field"><label>iPhone-Empfänger *</label>' +
        '<input name="notify_target" list="garten-notify-liste" maxlength="97" value="' +
        escapeHtml(a.notify_target) + '" placeholder="notify.angelinas_iphone_15_pro">' +
        '<datalist id="garten-notify-liste">' +
        options([...notifyEntities, ...notifyServices]) + '</datalist>' +
        '<div class="small">Eine vorhandene Notify-Entität oder ein Notify-Dienst. ' +
        'Der tatsächliche Name muss in Home Assistant existieren.</div></div>' +
        '<div class="field"><label>Wetterentität für die Frostprognose *</label>' +
        '<input name="weather_entity" list="garten-weather-liste" maxlength="98" value="' +
        escapeHtml(a.weather_entity) + '" placeholder="weather.home">' +
        '<datalist id="garten-weather-liste">' +
        options(weatherOptions) + '</datalist></div>' +
        '<div class="field check-field"><label><input type="checkbox" name="freitag_aktiv"' +
        (a.freitag_aktiv ? ' checked' : '') +
        '> Freitags 16:00 Uhr eine Pflegeübersicht schicken</label></div>' +
        '<div class="field check-field"><label><input type="checkbox" name="frost_aktiv"' +
        (a.frost_aktiv ? ' checked' : '') +
        '> Bei möglicher Frostgefahr eine Warnung schicken</label></div>' +
        '<div class="field"><label>Warnschwelle (°C, -5 bis +8)</label>' +
        '<input type="number" name="frost_grenze_c" min="-5" max="8" step="0.5" required value="' +
        escapeHtml(a.frost_grenze_c) + '"></div>' +
        '<div class="small">Frostprüfung täglich um 06:15 und 18:15 Uhr. ' +
        'Jede Vorhersage ist unsicher; es werden keine Schnitt- oder Düngeaufträge automatisch erzeugt.</div>' +
        '<div class="dialog-foot"><button class="btn ghost" type="button" data-action="close">Abbrechen</button>' +
        '<button class="btn primary" type="submit">Einstellungen speichern</button></div></form>';
    }

    _ruleForm() {
      const plants = (this._data.pflanzen || []).map((p) => ({ value: p.id, label: p.name }));
      const areas = (this._data.bereiche || []).map((a) => ({ value: a.id, label: a.name }));
      const prefill = this._modal?.prefill || {};
      const selectedRhythm = prefill.rhythmus || "tage";
      return '<form data-form="regel"><div class="form-grid">' +
        '<div class="field full"><label>Wiederkehrende Aufgabe *</label><input name="name" maxlength="200" required value="' +
        escapeHtml(prefill.name || "") + '" placeholder="z. B. Pflanzen kontrollieren"></div>' +
        '<div class="field"><label>Erste Fälligkeit *</label><input name="startdatum" type="date" required></div>' +
        '<div class="field"><label>Rhythmus</label><select name="rhythmus">' +
        '<option value="tage"' + (selectedRhythm === "tage" ? ' selected' : '') +
        '>Alle X Tage</option><option value="jaehrlich"' + (selectedRhythm === "jaehrlich" ? ' selected' : '') +
        '>Jedes Jahr</option></select></div>' +
        '<div class="field"><label>Intervall in Tagen</label><input name="intervall_tage" type="number" min="1" max="365" value="14"></div>' +
        '<div class="field"><label>Pflanze</label><select name="pflanzen_id">' +
        this._options(plants, prefill.pflanzen_id || null, true) + '</select></div>' +
        '<div class="field full"><label>Gartenbereich</label><select name="bereich_id">' +
        this._options(areas, prefill.bereich_id || null, true) + '</select></div>' +
        (prefill.pflegefeld ?
          '<input type="hidden" name="aufgabentyp" value="' +
          escapeHtml(prefill.aufgabentyp || "einfach") + '">' :
          '<div class="field full"><label>Wie soll die Aufgabe erledigt werden?</label>' +
          '<select name="aufgabentyp"><option value="einfach">Ein Klick – erledigt</option>' +
          '<option value="giesskontrolle">Gießkontrolle – gegossen / kein Wasser nötig</option>' +
          '</select></div>') + '</div>' +
        '<div class="notice">' + escapeHtml(this._modal?.careInfo ||
          "Diese Wiederholung wird von dir angelegt. Es werden keine ungeprüften Empfehlungen übernommen.") +
        '</div>' +
        '<div class="dialog-foot"><button type="button" class="btn ghost" data-action="close">Abbrechen</button>' +
        '<button type="submit" class="btn primary">Wiederholung speichern</button></div></form>';
    }

    _taskForm() {
      const plants = (this._data.pflanzen || []).map((p) => ({
        value: p.id, label: p.name
      }));
      const areas = (this._data.bereiche || []).map((a) => ({
        value: a.id, label: a.name
      }));
      return '<form data-form="aufgabe"><div class="form-grid">' +
        '<div class="field full"><label>Was muss erledigt werden? *</label>' +
        '<input name="name" required maxlength="200" placeholder="z. B. Kübelpflanzen gießen"></div>' +
        '<div class="field"><label>Fällig am (optional)</label><input type="date" name="faellig_am"></div>' +
        '<div class="field"><label>Pflanze</label><select name="pflanzen_id">' +
        this._options(plants, null, true) + '</select></div>' +
        '<div class="field full"><label>Gartenbereich</label><select name="bereich_id">' +
        this._options(areas, null, true) + '</select></div>' +
        '<div class="field full"><label>Wie soll die Aufgabe erledigt werden?</label>' +
        '<select name="aufgabentyp"><option value="einfach">Ein Klick – erledigt</option>' +
        '<option value="giesskontrolle">Gießkontrolle – gegossen / kein Wasser nötig</option>' +
        '</select></div></div>' +
        '<div class="notice">Diese Aufgabe wird manuell angelegt. Automatische artspezifische Pflegepläne folgen nach der Fachprüfung.</div>' +
        '<div class="dialog-foot"><button class="btn ghost" type="button" data-action="close">Abbrechen</button>' +
        '<button type="submit" class="btn primary">Aufgabe speichern</button></div></form>';
    }

    _waterForm() {
      const task = this._modal.existing;
      return '<div class="notice">Wie wurde die Gießkontrolle abgeschlossen? Das Ergebnis wird mit Datum in der Pflegehistorie gespeichert.</div>' +
        '<p class="task-name">' + escapeHtml(task.name) + '</p>' +
        '<div class="dialog-foot"><button type="button" class="btn ghost" data-action="close">Abbrechen</button>' +
        '<button type="button" class="btn" data-action="task-water-choice" data-result="kontrolliert_kein_wasser" data-id="' +
        escapeHtml(task.id) + '">Kontrolliert – kein Wasser nötig</button>' +
        '<button type="button" class="btn primary" data-action="task-water-choice" data-result="gegossen" data-id="' +
        escapeHtml(task.id) + '">Gegossen</button></div>';
    }

    _modalHTML() {
      if (!this._modal) return "";
      const type = this._modal.type;
      const title = type === "pflege" ? "Pflegewissen: " + (this._modal.existing?.name || "") : type === "pflanze"
        ? (this._modal.existing ? "Pflanze bearbeiten" : "Neue Pflanze")
        : type === "saisonanker" ? "Frost-Referenzdaten" : type === "saison" ? "Saisonfenster vormerken" : type === "automatik" ? "Automatische Benachrichtigungen" : type === "giessen" ? "Gießkontrolle abschließen" : type === "regel" ? "Neue Wiederholung" : type === "aufgabe" ? "Neue Pflegeaufgabe" : "Neuer Gartenbereich";
      let body = "";
      if (type === "pflege") body = this._careHTML();
      else if (type === "pflanze") body = this._plantForm();
      else if (type === "automatik") body = this._automatikForm();
      else if (type === "saisonanker") body = this._saisonankerForm();
      else if (type === "saison") body = this._saisonForm();
      else if (type === "regel") body = this._ruleForm();
      else if (type === "aufgabe") body = this._taskForm();
      else if (type === "giessen") body = this._waterForm();
      else body = '<form data-form="bereich"><div class="field"><label>Bereichsname *</label>' +
        '<input name="name" required maxlength="120" placeholder="z. B. Hochbeet, Terrasse, Vorgarten"></div>' +
        '<div class="dialog-foot"><button type="button" data-action="close" class="btn ghost">Abbrechen</button>' +
        '<button type="submit" class="btn primary">Bereich anlegen</button></div></form>';
      return '<div class="modal-backdrop"><section class="dialog" role="dialog" aria-modal="true" aria-label="' +
        escapeHtml(title) + '"><div class="heading"><h2>' + escapeHtml(title) +
        '</h2><button type="button" class="btn tiny ghost" data-action="close" aria-label="Schließen">✕</button></div>' +
        body + '</section></div>';
    }

    _taskHTML(task) {
      const isDone = task.status === "erledigt";
      const linked = this._getPlant(task.pflanzen_id);
      const due = task.faellig_am || null;
      const overdue = !isDone && due && due < dateToday();
      return '<div class="task' + (isDone ? " done" : "") + '"><div>' +
        '<div class="task-name">' + escapeHtml(task.name) + "</div>" +
        '<div class="task-meta">' + escapeHtml(dateLabel(due)) +
        (linked ? " · " + escapeHtml(linked.name) : "") +
        (task.herkunft === "wetterprognose" ?
          ' <span class="tag">Wetterprognose, keine bestätigte Frostwarnung</span>' : "") +
        (task.pflegebezug ?
          ' <span class="tag">Quellenhinweis: ' +
          escapeHtml(task.pflegebezug.quelle || "unbekannt") +
          ' · nicht fachlich geprüft</span>' : "") +
        (task.saisonbezug ?
          ' <span class="tag">Saisonkontrolle · ' +
          escapeHtml(task.saisonbezug.quelle || "unbekannt") +
          ' · unverbindlicher Planungstermin</span>' : "") +
        (overdue ? ' <span class="tag">Überfällig</span>' : "") +
        (isDone && task.ergebnis === "gegossen" ? ' <span class="chip">Gegossen</span>' : "") +
        (isDone && task.ergebnis === "kontrolliert_kein_wasser" ?
          ' <span class="chip">Kontrolliert – kein Wasser nötig</span>' : "") +
        '</div></div><div class="buttons">' +
        '<button class="btn tiny" type="button" data-action="' +
        (isDone ? "task-reopen" :
          task.aufgabentyp === "giesskontrolle" ? "task-result" : "task-done") +
        '" data-id="' + escapeHtml(task.id) + '">' +
        (isDone ? "Wieder öffnen" : task.aufgabentyp === "giesskontrolle" ? "Kontrollieren" : "Erledigt") +
        "</button>" +
        '<button class="btn ghost tiny danger" type="button" aria-label="Aufgabe entfernen" data-action="task-remove" data-id="' +
        escapeHtml(task.id) + '">✕</button></div></div>';
    }

    _homeHTML() {
      const plants = this._data.pflanzen || [];
      const tasks = this._data.aufgaben || [];
      const pending = tasks.filter((t) => t.status !== "erledigt").sort(byDate);
      const done = tasks.filter((t) => t.status === "erledigt").slice(-4).reverse();
      const areas = this._data.bereiche || [];
      return '<div class="stats">' +
        '<div class="stat"><div class="count">' + plants.length + '</div><div class="label">Pflanzen</div></div>' +
        '<div class="stat"><div class="count">' + pending.length + '</div><div class="label">Offene Aufgaben</div></div>' +
        '<div class="stat"><div class="count">' + areas.length + '</div><div class="label">Gartenbereiche</div></div>' +
        '</div><div class="heading"><h2>Willkommen in deinem Garten</h2>' +
        '<button class="btn primary" data-action="plant-new">＋ Pflanze hinzufügen</button></div>' +
        '<div class="grid">' +
        '<section class="card"><h3>🌱 Anstehende Pflege</h3>' +
        (pending.length ? pending.slice(0, 6).map((t) => this._taskHTML(t)).join("")
          : '<div class="small">Aktuell sind keine Pflegeaufgaben offen.</div>') +
        '<div class="footer"><button class="btn tiny" data-action="task-new">＋ Aufgabe anlegen</button>' +
        '<button class="btn tiny ghost" data-action="tab" data-tab="kalender">Alle Aufgaben</button></div></section>' +
        '<section class="card"><h3>🍃 Zuletzt erledigt</h3>' +
        (done.length ? done.map((t) => this._taskHTML(t)).join("")
          : '<p>Deine erledigten Gartenaufgaben werden hier angezeigt.</p>') +
        '<hr class="line"><h3>Pflegewissen</h3><p>Deutsche Pflegeinformationen kannst du bei jeder erfassten Pflanze öffnen. ' +
        'Soweit verfügbar stammen sie aus OpenPlantbook und sind als nicht fachlich geprüft gekennzeichnet.</p>' +
        '<span class="chip muted">Fachprüfung noch offen</span></section></div>';
    }

    _plantsHTML() {
      const plants = this._data.pflanzen || [];
      let html = '<div class="heading"><h2>Meine Pflanzen</h2>' +
        '<button class="btn primary" data-action="plant-new">＋ Pflanze hinzufügen</button></div>';
      if (!plants.length) return html + '<div class="empty"><div class="symbol">🌱</div>' +
        'Noch keine Pflanzen erfasst. Lege die erste Pflanze per deutscher Namenssuche an.</div>';
      const groups = [...new Set(plants.map((p) => p.gruppe || "Weitere Pflanzen"))];
      for (const group of groups) {
        const entries = plants.filter((p) => (p.gruppe || "Weitere Pflanzen") === group);
        html += '<div class="section"><h3 class="section-title">' + escapeHtml(group) +
          '</h3><div class="grid">' + entries.map((p) => {
            const area = this._getArea(p.bereich_id);
            return '<section class="card"><h3>🌿 ' + escapeHtml(p.name) + '</h3>' +
              (p.wissenschaftlich ? '<p><em>' + escapeHtml(p.wissenschaftlich) + '</em></p>' : "") +
              '<span class="chip">' + escapeHtml(area ? area.name : "Nicht zugeordnet") + '</span>' +
              (p.notizen ? '<p style="margin-top:12px;white-space:pre-wrap">' + escapeHtml(p.notizen) + '</p>' : "") +
              '<div class="footer"><button class="btn tiny" data-action="care-open" data-id="' +
              escapeHtml(p.id) + '">Pflegewissen</button><button class="btn tiny" data-action="plant-edit" data-id="' +
              escapeHtml(p.id) + '">Bearbeiten</button>' +
              '<button class="btn ghost tiny danger" data-action="plant-remove" data-id="' +
              escapeHtml(p.id) + '">Entfernen</button></div></section>';
          }).join("") + '</div></div>';
      }
      return html;
    }

    _saisonHTML() {
      const saison = this._saison;
      if (!saison) return "";
      const hits = saison.vorschlaege || [];
      const active = hits.filter((r) => r.fenster_von);
      const noDates = hits.filter((r) => !r.fenster_von);
      return '<section class="card" style="margin:0 0 14px"><div class="heading">' +
        '<h3>🌾 Saisonfenster (' + active.length + ')</h3>' +
        '<button type="button" class="btn tiny" data-action="saisonanker-open">⚙ Frost-Referenzdaten</button>' +
        '</div><p class="small">OpenPlantDB · CC0 1.0 · aus botanisch exakt zugeordneten Pflanzen. ' +
        'Die US-Ausgangsdaten sind für deinen Garten nicht regional geprüft. ' +
        'Keine Tätigkeit wird ohne Bestätigung angelegt.</p>' +
        (hits.length === 0 ?
          '<div class="small">Für die erfassten Pflanzen liegen noch keine eindeutig passenden, strukturierten Saisonfenster vor. ' +
          'Alle Pflanzen bleiben manuell verwaltbar.</div>' : "") +
        (noDates.length ?
          '<div class="notice">Für ' + noDates.length +
          ' Pflanze(n) fehlt das passende Frost-Referenzdatum. ' +
          'Bitte die Referenztage für das gewünschte Jahr selbst festlegen.</div>' : "") +
        (active.length ? active.slice(0, 40).map((r) =>
          '<div class="task"><div><div class="task-name">' +
          escapeHtml(r.titel) + ' – ' + escapeHtml(r.pflanze) + '</div>' +
          '<div class="task-meta"><em>' + escapeHtml(r.wissenschaftlich) + '</em> · ' +
          escapeHtml(dateLabel(r.fenster_von)) + ' – ' +
          escapeHtml(dateLabel(r.fenster_bis)) +
          ' · Quelle: OpenPlantDB (CC0), nicht regional geprüft</div></div>' +
          '<button class="btn tiny" type="button" data-action="saison-plan" data-id="' +
          escapeHtml(r.pflanzen_id) + '" data-katalog="' +
          escapeHtml(r.katalog_id) + '"' +
          (r.vorgemerkt ? ' disabled' : '') + '>' +
          (r.vorgemerkt ? 'Vorgemerkt' : 'Kontrolle planen') +
          '</button></div>'
        ).join("") : "") + '</section>';
    }

    _calendarHTML() {
      const tasks = [...(this._data.aufgaben || [])].sort(byDate);
      const pending = tasks.filter((t) => t.status !== "erledigt");
      const done = tasks.filter((t) => t.status === "erledigt");
      const rules = this._data.regeln || [];
      return '<div class="heading"><h2>Pflegekalender</h2>' +
        '<div class="buttons"><button class="btn ghost" data-action="automatik-open">⚙ Benachrichtigungen</button><button class="btn" data-action="rule-new">＋ Wiederholung anlegen</button><button class="btn primary" data-action="task-new">＋ Aufgabe anlegen</button></div></div>' +
        '<div class="notice">Manuelle Aufgaben und deine Wiederholungen werden angezeigt. ' +
        'Frostprognosen und Freitagsberichte lassen sich über Benachrichtigungen einschalten. ' +
        'Artspezifische Schnitt- und Düngeaufgaben bleiben bis zur Fachprüfung gesperrt.</div>' +
        this._saisonHTML() +
        '<div class="grid"><section class="card"><h3>Offene Aufgaben (' + pending.length + ')</h3>' +
        (pending.length ? pending.map((t) => this._taskHTML(t)).join("")
          : '<p>Keine offenen Aufgaben.</p>') + '</section>' +
        '<section class="card"><h3>Erledigte Aufgaben (' + done.length + ')</h3>' +
        (done.length ? done.slice().reverse().map((t) => this._taskHTML(t)).join("")
          : '<p>Hier erscheint später die Pflegehistorie.</p>') + '</section></div>' +
        '<section class="card" style="margin-top:14px"><h3>Meine Wiederholungen (' + rules.length + ')</h3>' +
        (rules.length ? rules.map((r) => '<div class="task"><div><div class="task-name">' + escapeHtml(r.name) +
          '</div><div class="task-meta">' + escapeHtml(r.rhythmus === 'tage' ? 'Alle ' + r.intervall_tage + ' Tage' : 'Jährlich') +
          ' · Start ' + escapeHtml(dateLabel(r.startdatum)) +
          (r.pflegebezug ? ' · Aus Pflegewissen (nicht fachlich geprüft)' : '') +
          (r.aktiv ? '' : ' · Pausiert') +
          '</div></div><div class="buttons"><button class="btn tiny" data-action="rule-toggle" data-id="' + escapeHtml(r.id) + '">' +
          (r.aktiv ? 'Pausieren' : 'Aktivieren') + '</button><button class="btn ghost tiny danger" data-action="rule-remove" data-id="' +
          escapeHtml(r.id) + '">Entfernen</button></div></div>').join('') : '<p>Keine Wiederholungen vorhanden.</p>') + '</section>';
    }

    _areasHTML() {
      const areas = this._data.bereiche || [];
      const plants = this._data.pflanzen || [];
      let html = '<div class="heading"><h2>Gartenbereiche</h2>' +
        '<button class="btn primary" data-action="area-new">＋ Bereich anlegen</button></div>';
      if (!areas.length) {
        return html + '<div class="empty"><div class="symbol">🪴</div>' +
          'Noch keine Bereiche. Du kannst sie jederzeit anlegen, umbenennen oder entfernen.</div>';
      }
      html += '<div class="grid">';
      for (const area of areas) {
        const assigned = plants.filter((p) => p.bereich_id === area.id);
        html += '<section class="card"><h3>🪴 ' + escapeHtml(area.name) + '</h3>' +
          '<p>' + assigned.length + ' Pflanzen zugeordnet</p>' +
          (assigned.length ? '<p class="small">' +
            escapeHtml(assigned.slice(0, 5).map((p) => p.name).join(" · ")) +
            (assigned.length > 5 ? " …" : "") + '</p>' : "") +
          '<div class="footer"><button class="btn tiny" data-action="area-rename" data-id="' +
          escapeHtml(area.id) + '">Umbenennen</button>' +
          '<button class="btn tiny ghost danger" data-action="area-remove" data-id="' +
          escapeHtml(area.id) + '">Entfernen</button></div></section>';
      }
      return html + '</div>';
    }

    _render() {
      if (!this.shadowRoot) return;
      const nav = [
        ["start", "⌂ Start"],
        ["pflanzen", "🌿 Pflanzen"],
        ["kalender", "▦ Kalender"],
        ["bereiche", "▤ Bereiche"],
      ];
      const tabs = nav.map(([key, title]) =>
        '<button class="tab" role="tab" aria-selected="' +
        (this._tab === key ? "true" : "false") + '" data-action="tab" data-tab="' +
        key + '">' + title + "</button>"
      ).join("");
      const main = !this._data
        ? '<div class="empty"><div class="symbol">🌱</div>Gartenbackend wird verbunden …</div>'
        : this._tab === "pflanzen" ? this._plantsHTML()
          : this._tab === "kalender" ? this._calendarHTML()
            : this._tab === "bereiche" ? this._areasHTML() : this._homeHTML();
      this.shadowRoot.innerHTML = '<style>' + CSS + '</style>' +
        '<main class="garden"><header class="hero"><div>' +
        '<div class="eyebrow">Mein Garten · Home Assistant</div>' +
        '<h1>Dein Garten. Alles im Blick.</h1>' +
        '<div class="sub">Pflanzen, Pflege und Gartenbereiche an einem Ort.</div></div>' +
        '<div class="hero-icon" aria-hidden="true">🌿</div></header>' +
        '<nav role="tablist" class="tabs" aria-label="Mein Garten">' + tabs + '</nav>' +
        (this._error ? '<div role="alert" class="error">' + escapeHtml(this._error) + '</div>' : "") +
        main + (this._modal && this._data ? this._modalHTML() : "") +
        '</main>';
    }
  }

  if (!customElements.get("mein-garten-v1-card")) {
    customElements.define("mein-garten-v1-card", MeinGartenCard);
  }
  window.customCards = window.customCards || [];
  if (!window.customCards.some((x) => x.type === "mein-garten-v1-card")) {
    window.customCards.push({
      type: "mein-garten-v1-card",
      name: "Mein Garten",
      description: "Eigenständige Gartenverwaltung mit Pflanzen, Bereichen, Aufgaben und Kalender."
    });
  }
})();
