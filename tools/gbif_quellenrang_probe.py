"""Diagnose der Quellreihenfolge, damit zusätzliche Trivialnamen keine alten Treffer verdrängen."""
from __future__ import annotations
import asyncio
import json

from tools.pflanzensuche_50_live import BenchmarkSuche
from custom_components.mein_garten.search import _dedupe, _norm

CASES = [
    ("Frauenmantel", "Alchemilla mollis"),
    ("Fetthenne", "Hylotelephium spectabile"),
    ("Felsenbirne", "Amelanchier lamarckii"),
    ("Apfelbaum", "Malus domestica"),
    ("Engelstrompete", "Brugmansia suaveolens"),
    ("Süßkirsche", "Prunus avium"),
]


async def run():
    service = BenchmarkSuche(object())
    for query, expected in CASES:
        data = await asyncio.gather(
            service._i_nat(query), service._wikidata(query),
            service._gbif(query), service._gbif_vernacular(query),
            return_exceptions=True,
        )
        providers = ["iNaturalist", "Wikidata", "GBIF scientific", "GBIF vernacular"]
        for provider, result in zip(providers, data):
            if isinstance(result, BaseException):
                print(json.dumps({"frage": query, "quelle": provider,
                    "fehler": type(result).__name__}, ensure_ascii=False), flush=True)
                continue
            normalized = _dedupe(result)
            rank = next((i+1 for i, x in enumerate(normalized)
                         if _norm(x["wissenschaftlich"]) == _norm(expected)), None)
            print(json.dumps({"frage": query, "quelle": provider,
                "anzahl": len(normalized), "rang_erwartete_art": rank,
                "top15": [{
                    "wissenschaftlich": x["wissenschaftlich"],
                    "deutsch": x["deutsch"]
                } for x in normalized[:15]]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(run())
