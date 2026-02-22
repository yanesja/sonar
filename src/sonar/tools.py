"""
tools.py - Sonar agent tools.

Each tool takes a constructed request as input and executes it,
returning a JSON string. Mirrors the execute_es_query pattern in ConnectChat.
"""

import json

import httpx
from langchain_core.tools import tool


@tool
async def execute_sighting_request(url: str) -> str:
    """
    Execute a Whale Hotline API request and return results.

    Args:
        url: Complete URL with query parameters already constructed.
             Example: "http://hotline.whalemuseum.org/api.json?species=orca&limit=5"

    Returns:
        JSON string with sighting data or error message.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Count endpoint returns a plain int — wrap it
        if isinstance(data, int):
            return json.dumps({"success": True, "count": data})

        # Sightings list — trim fields to keep tokens low
        if isinstance(data, list):
            trimmed = [
                {
                    "id": s.get("id"),
                    "species": s.get("species"),
                    "quantity": s.get("quantity"),
                    "orca_type": s.get("orca_type"),
                    "pod": s.get("pod"),
                    "description": s.get("description"),
                    "sighted_at": s.get("sighted_at"),
                    "location": s.get("location"),
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                }
                for s in data
            ]
            return json.dumps(
                {"success": True, "count": len(trimmed), "sightings": trimmed},
                indent=2,
            )

        # Single sighting object
        return json.dumps({"success": True, "sighting": data}, indent=2)

    except httpx.HTTPStatusError as e:
        return json.dumps(
            {"success": False, "error": f"HTTP {e.response.status_code}: {e.response.text}"}
        )
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})