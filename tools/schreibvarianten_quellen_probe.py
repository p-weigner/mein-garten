"""Reale Varianten der bestehenden Quellen, ohne neue Anbieter oder Sondernamen im Produkt."""
import asyncio
import json
from tools.pflanzensuche_50_live import BenchmarkSuche
from custom_components.mein_garten.search import _norm

QUERIES = [
    ("Rispen-Hortensie", "Hydrangea paniculata"),
    ("Rispen Hortensie", "Hydrangea paniculata"),
    ("Rispen", "Hydrangea paniculata"),
    ("Fächerahorn", "Acer palmatum"),
    ("Fächer-Ahorn", "Acer palmatum"),
    ("Japanischer Ahorn", "Acer palmatum"),
]

async def run():
    service = BenchmarkSuche(object())
    for text, expected in QUERIES:
        results = await asyncio.gather(
            service._i_nat(text), service._gbif_vernacular(text),
            service._gbif(text), return_exceptions=True,
        )
        for label, x in zip(("iNaturalist", "GBIF-Trivialnamen", "GBIF-Namen"), results):
            if isinstance(x, BaseException):
                print(json.dumps({"query": text, "quelle": label,
                                  "fehler": type(x).__name__}, ensure_ascii=False), flush=True)
                continue
            names = [v["wissenschaftlich"] for v in x]
            rank = next((i + 1 for i,v in enumerate(x)
                         if _norm(v["wissenschaftlich"]) == _norm(expected)), None)
            print(json.dumps({
                "query": text, "quelle": label, "gefunden": len(names),
                "erwartete_art_rang": rank, "top5": names[:5],
            }, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    asyncio.run(run())
