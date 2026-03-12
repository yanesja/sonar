"""
tools.py - Sonar agent tools.

Each tool takes a constructed request as input and executes it,
returning a JSON string. Mirrors the execute_es_query pattern in ConnectChat.
"""

import json

import httpx
from langchain_core.tools import tool

# Fields to keep from each observation record — keeps tool responses token-efficient
_OBSERVATION_FIELDS = (
    "id",
    "observed_on",
    "place_guess",
    "quality_grade",
    "uri",
    "taxon_name",
    "taxon_common_name",
    "individual_count",
    "description",
    "latitude",
    "longitude",
)


def _trim_observation(obs: dict) -> dict:
    """Pull the fields we care about from a raw iNaturalist observation record."""
    taxon = obs.get("taxon") or {}

    # location is a "lat,lon" string — split it out
    location_str = obs.get("location")
    lat, lon = location_str.split(",") if location_str else (None, None)

    return {
        "id": obs.get("id"),
        "observed_on": obs.get("observed_on"),
        "place_guess": obs.get("place_guess"),
        "quality_grade": obs.get("quality_grade"),
        "uri": obs.get("uri"),
        "taxon_name": taxon.get("name"),
        "taxon_common_name": taxon.get("preferred_common_name"),
        "description": obs.get("description"),
        "latitude": lat,
        "longitude": lon,
    }


@tool
async def execute_sighting_request(url: str) -> str:
    """
    Execute an iNaturalist API request and return results.

    Args:
        url: Complete URL with query parameters already constructed.
             Example: "https://api.inaturalist.org/v1/observations?taxon_name=Orcinus+orca&per_page=5"

    Returns:
        JSON string with sighting data or error message.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        total = data.get("total_results")
        results = data.get("results", [])

        # Histogram endpoint — results is a dict keyed by interval (e.g. "year")
        if isinstance(results, dict):
            return json.dumps({"success": True, "total_results": total, "histogram": results})

        # Count-only query (per_page=0) — just return the total
        if not results:
            return json.dumps({"success": True, "total_results": total})

        # Observation list — trim each record to keep tokens low
        if isinstance(results, list) and results and isinstance(results[0], dict):
            # Species counts endpoint returns {count, taxon} dicts, not observation dicts
            if "taxon" in results[0]:
                trimmed = [
                    {
                        "taxon_name": r["taxon"].get("name"),
                        "common_name": r["taxon"].get("preferred_common_name"),
                        "count": r.get("count"),
                    }
                    for r in results
                ]
                return json.dumps(
                    {"success": True, "total_results": total, "species_counts": trimmed},
                    indent=2,
                )

            # Standard observation records
            trimmed = [_trim_observation(obs) for obs in results]
            return json.dumps(
                {"success": True, "total_results": total, "observations": trimmed},
                indent=2,
            )

        return json.dumps({"success": True, "total_results": total, "results": results})

    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})