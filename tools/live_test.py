"""Reproduzierbarer öffentlicher Live-Test botanischer Arten (nur Standardbibliothek)."""
import csv, datetime as dt, html, json, pathlib, time, urllib.parse, urllib.request, urllib.error

ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/"berichte"
PLANTS=json.loads((ROOT/"daten"/"testpflanzen.json").read_text(encoding="utf-8"))
HEADERS={"User-Agent":"MeinGarten-SourceStudy/1.0 (public research; no personal data)","Accept":"application/json"}
def fetch(url):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=18) as r:
        if r.status!=200: raise RuntimeError("HTTP "+str(r.status))
        payload=r.read(600_001)
        if len(payload)>600_000: raise RuntimeError("Antwort zu gross")
    return json.loads(payload)
def norm(v): return " ".join(str(v or "").casefold().replace("×"," x ").split())
def exact(candidate, expected, rank):
    return norm(candidate)==norm(expected) and str(rank).lower() in ("species","subspecies","variety","form","hybrid")
def hybrid_variante(candidate, expected):
    a, b = norm(candidate), norm(expected)
    return (" x " in a or " x " in b) and a.replace(" x ", " ") == b.replace(" x ", " ")
def check_gbif(name):
    url="https://api.gbif.org/v1/species/match?"+urllib.parse.urlencode({"name":name,"kingdom":"Plantae","strict":"true"})
    data=fetch(url)
    found=data.get("canonicalName") or ""
    status = "nicht_eindeutig"
    if data.get("matchType") == "EXACT" and exact(found, name, data.get("rank")):
        status = "exakt"
    elif (data.get("matchType") == "EXACT" and str(data.get("rank")).lower() in ("species", "hybrid")
          and (data.get("confidence") or 0) >= 99 and hybrid_variante(found, name)):
        status = "hybrid_schreibweise"
    return {"status":status,"name":found,"id":data.get("usageKey"),"matchType":data.get("matchType"),"confidence":data.get("confidence"),"url":"https://www.gbif.org/species/"+str(data.get("usageKey")) if data.get("usageKey") else ""}
def check_inat(name):
    url="https://api.inaturalist.org/v1/taxa/autocomplete?"+urllib.parse.urlencode({"q":name,"locale":"de","per_page":15})
    data=fetch(url)
    results=data.get("results",[])
    for entry in results:
        if exact(entry.get("name"),name,entry.get("rank")):
            return {"status":"exakt","name":entry.get("name"),"id":entry.get("id"),"deutscher_name":entry.get("preferred_common_name") or "","url":"https://www.inaturalist.org/taxa/"+str(entry.get("id"))}
    return {"status":"nicht_eindeutig","name":results[0].get("name","") if results else "","deutscher_name":"","url":""}
def run():
    OUT.mkdir(exist_ok=True)
    rows=[]
    for i,p in enumerate(PLANTS,1):
        row=dict(p)
        for source,fn in [("gbif",check_gbif),("inat",check_inat)]:
            try:
                value=fn(p["wissenschaftlich"]);row[source+"_status"]=value.pop("status");row[source+"_details"]=value;row[source+"_fehler"]=""
            except Exception as exc:
                row[source+"_status"]="fehler";row[source+"_details"]={};row[source+"_fehler"]=type(exc).__name__+": "+str(exc)[:180]
            time.sleep(.22)
        rows.append(row)
        print(f"{i:02d}/{len(PLANTS)} {p['wissenschaftlich']} | GBIF={row['gbif_status']} | iNaturalist={row['inat_status']}",flush=True)
        for source in ("gbif", "inat"):
            if row[source+"_status"] == "nicht_eindeutig":
                info = row[source+"_details"]
                # Nur öffentliche botanische Kandidatennamen, keine Schlüssel oder privaten Daten.
                print(f"  {source}: Kandidat={info.get('name', '')!r}, Matchtyp={info.get('matchType', '')!r}, Konfidenz={info.get('confidence', '')!r}", flush=True)
    timestamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    summary={s:{state:sum(r[s+"_status"]==state for r in rows) for state in ("exakt","hybrid_schreibweise","nicht_eindeutig","fehler")} for s in ("gbif","inat")}
    result={"zeitpunkt_utc":timestamp,"hinweis":"Botanischer Namensabgleich; keine Prüfung von Pflegewissen oder Übersetzung.","gesamt":len(rows),"statistik":summary,"pflanzen":rows}
    (OUT/"datenquellen.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    with (OUT/"datenquellen.csv").open("w",newline="",encoding="utf-8-sig") as f:
        columns=["gruppe","name_de","wissenschaftlich","gbif_status","inat_status","gbif_fehler","inat_fehler"]
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore");writer.writeheader();writer.writerows(rows)
    text=["# Mein Garten – öffentlicher API-Livetest", "",f"**Zeitpunkt (UTC):** {timestamp}",f"**Pflanzen:** {len(rows)}","","> Nur botanische Namensidentität; KEINE Pflege- oder Übersetzungsprüfung.","","| Quelle | Exakt | Hybrid-Schreibweise | Nicht eindeutig | Fehler |","|---|---:|---:|---:|---:|"]
    for s in ("gbif","inat"):
        x=summary[s];text.append(f"| {s} | {x['exakt']} | {x['hybrid_schreibweise']} | {x['nicht_eindeutig']} | {x['fehler']} |")
    text += ["","| Pflanze | GBIF | iNaturalist |","|---|---|---|"]
    for row in rows:text.append(f"| {row['wissenschaftlich']} | {row['gbif_status']} | {row['inat_status']} |")
    text+=["","## Fehler"]
    for row in rows:
        for source in ("gbif","inat"):
            if row[source+"_fehler"]:text.append(f"- {row['wissenschaftlich']} / {source}: {row[source+'_fehler']}")
    (OUT/"datenquellen.md").write_text("\n".join(text)+"\n",encoding="utf-8")
    (OUT/"datenquellen.html").write_text("<!doctype html><html lang='de'><meta charset='utf-8'><title>Mein Garten – API-Test</title><style>body{font:16px system-ui;max-width:1100px;margin:3em auto;background:#242320;color:#f0ede6}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #3b3934;padding:9px;text-align:left}</style><h1>Mein Garten – Datenquellen-Livetest</h1><p>Nur botanische Namenssuche, keine Pflegequalität geprüft.</p><table><tr><th>Pflanze</th><th>GBIF</th><th>iNaturalist</th></tr>"+ "".join("<tr>"+ "".join("<td>"+html.escape(str(v))+"</td>" for v in (r["wissenschaftlich"],r["gbif_status"],r["inat_status"]))+"</tr>" for r in rows)+"</table></html>",encoding="utf-8")
    print("Berichte erstellt:",OUT.resolve(),flush=True)
    # Einzelne API-Fehler zählen als Daten. Totaler API-Ausfall ist ein echter Testfehler.
    if not any(r[s+"_status"]!="fehler" for r in rows for s in ("gbif","inat")):raise SystemExit("Beide Quellen unerreichbar")
if __name__=="__main__":run()
