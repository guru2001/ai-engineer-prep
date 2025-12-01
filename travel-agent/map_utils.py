"""Google Maps integration utilities for generating map URLs and geocoding."""

import os
import urllib.parse
from typing import TYPE_CHECKING, List, Optional, Tuple, Union
from dotenv import load_dotenv

if TYPE_CHECKING:
    from city_extractor import Place

# Load environment variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")


def _build_search_query(place: Union[str, "Place"]) -> str:
    """
    Build an optimized search query from a Place object or string.
    
    Args:
        place: Either a Place object or a string
    
    Returns:
        Search query string optimized for geocoding
    """
    # Handle string input for backward compatibility
    if isinstance(place, str):
        return place
    
    # Build query from Place object with context
    query_parts = [place.name]
    
    # Add country/region context if available
    if place.country:
        query_parts.append(place.country)
    
    # Add type context if it helps disambiguate
    if place.type and place.type not in ["city", "town"]:
        # For landmarks/attractions, type can help but don't always include it
        # as it might make the query too specific
        pass
    
    # Add additional context if available and helpful
    if place.context:
        # Only add context if it's short and specific (not redundant)
        context = place.context.strip()
        if len(context) < 50 and context.lower() not in place.name.lower():
            query_parts.append(context)
    
    return ", ".join(query_parts)


def geocode_city(place: Union[str, "Place"]) -> Optional[Tuple[float, float]]:
    """
    Geocode a place name to get its coordinates using Google Geocoding API.
    
    Args:
        place: Either a Place object with context or a string with place name
    
    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Warning: GOOGLE_MAPS_API_KEY not found in environment variables")
        return None
    
    # Build optimized search query
    search_query = _build_search_query(place)
    
    try:
        import requests
        
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": search_query,
            "key": GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])
    except Exception as e:
        place_name = place.name if hasattr(place, "name") else str(place)
        print(f"Error geocoding {place_name}: {e}")
    
    return None


def generate_google_maps_url(cities: List[Union[str, "Place"]], use_embed: bool = False) -> str:
    """
    Generate a Google Maps URL with markers for multiple places.
    
    Args:
        cities: List of place names (strings) or Place objects
        use_embed: If True, generate embed URL. If False, generate regular map URL.
    
    Returns:
        Google Maps URL string
    """
    if not cities:
        return "https://www.google.com/maps"
    
    # Geocode all places to get coordinates
    coordinates = []
    for place in cities:
        coords = geocode_city(place)
        if coords:
            # Store the place name for display
            place_name = place.name if hasattr(place, "name") else str(place)
            coordinates.append((place_name, coords))
    
    if not coordinates:
        # Fallback: use search query if geocoding fails
        if len(cities) == 1:
            place = cities[0]
            search_query = _build_search_query(place)
            city_query = urllib.parse.quote(search_query)
            return f"https://www.google.com/maps/search/?api=1&query={city_query}"
        else:
            # Multiple places - use directions mode
            waypoints = "|".join([urllib.parse.quote(_build_search_query(place)) for place in cities])
            return f"https://www.google.com/maps/dir/{waypoints}"
    
    if use_embed:
        # Generate embed URL with markers using Google Maps Embed API
        if not GOOGLE_MAPS_API_KEY:
            # Without API key, we can't use Embed API - return None to trigger fallback
            return None
        
        if not coordinates:
            # If geocoding failed, try to use directions embed with place names
            if len(cities) >= 2:
                origin = urllib.parse.quote(_build_search_query(cities[0]))
                destination = urllib.parse.quote(_build_search_query(cities[-1]))
                waypoints = "|".join([urllib.parse.quote(_build_search_query(place)) for place in cities[1:-1]]) if len(cities) > 2 else ""
                if waypoints:
                    return f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={origin}&destination={destination}&waypoints={waypoints}"
                else:
                    return f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={origin}&destination={destination}"
            elif len(cities) == 1:
                # Single place - use place search
                search_query = _build_search_query(cities[0])
                place = urllib.parse.quote(search_query)
                return f"https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_API_KEY}&q={place}"
        
        # Generate embed URL with markers
        markers = []
        for city, (lat, lng) in coordinates:
            markers.append(f"{lat},{lng}")
        
        markers_str = "|".join(markers)
        center_lat = sum(lat for _, (lat, _) in coordinates) / len(coordinates)
        center_lng = sum(lng for _, (_, lng) in coordinates) / len(coordinates)
        
        # Use Google Maps Embed API v1 with proper format
        # For multiple markers, we use the view endpoint
        return (
            f"https://www.google.com/maps/embed/v1/view?"
            f"key={GOOGLE_MAPS_API_KEY}&"
            f"center={center_lat},{center_lng}&"
            f"zoom=6&"
            f"markers={markers_str}"
        )
    else:
        # Generate regular Google Maps URL with multiple destinations
        if len(coordinates) == 1:
            city, (lat, lng) = coordinates[0]
            return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
        else:
            # Use directions mode with waypoints
            waypoints = []
            for city, (lat, lng) in coordinates:
                waypoints.append(f"{lat},{lng}")
            
            # Start from first city, end at last city, with others as waypoints
            start = waypoints[0]
            end = waypoints[-1]
            waypoints_mid = waypoints[1:-1] if len(waypoints) > 2 else []
            
            if waypoints_mid:
                waypoints_str = "|".join(waypoints_mid)
                return (
                    f"https://www.google.com/maps/dir/{start}/{waypoints_str}/{end}"
                )
            else:
                return f"https://www.google.com/maps/dir/{start}/{end}"


def get_map_urls(cities: List[Union[str, "Place"]]) -> Tuple[str, str]:
    """
    Get both embed URL and regular map URL for places.
    
    Args:
        cities: List of place names (strings) or Place objects
    
    Returns:
        Tuple of (embed_url, map_url)
    """
    embed_url = generate_google_maps_url(cities, use_embed=True)
    map_url = generate_google_maps_url(cities, use_embed=False)
    
    # Debug logging
    print(f"Generated embed_url: {embed_url}")
    print(f"Generated map_url: {map_url}")
    print(f"Has API key: {bool(GOOGLE_MAPS_API_KEY)}")
    
    # If embed URL is None but we have API key, try to generate a fallback embed URL
    if not embed_url and GOOGLE_MAPS_API_KEY:
        print("Embed URL is None but API key exists - trying fallback generation")
        # Try using directions embed API directly with place names
        if len(cities) >= 2:
            origin = urllib.parse.quote(_build_search_query(cities[0]))
            destination = urllib.parse.quote(_build_search_query(cities[-1]))
            waypoints = "|".join([urllib.parse.quote(_build_search_query(place)) for place in cities[1:-1]]) if len(cities) > 2 else ""
            if waypoints:
                embed_url = f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={origin}&destination={destination}&waypoints={waypoints}"
            else:
                embed_url = f"https://www.google.com/maps/embed/v1/directions?key={GOOGLE_MAPS_API_KEY}&origin={origin}&destination={destination}"
        elif len(cities) == 1:
            search_query = _build_search_query(cities[0])
            place = urllib.parse.quote(search_query)
            embed_url = f"https://www.google.com/maps/embed/v1/place?key={GOOGLE_MAPS_API_KEY}&q={place}"
        print(f"Fallback embed_url: {embed_url}")
    
    return (embed_url or "", map_url)


def generate_shareable_map_html(cities: List[Union[str, "Place"]], width: str = "100%", height: str = "400px") -> str:
    """
    Generate HTML for an embedded Google Maps iframe with places marked.
    
    Args:
        cities: List of place names (strings) or Place objects
        width: Width of the map iframe
        height: Height of the map iframe
    
    Returns:
        HTML string with embedded map
    """
    if not GOOGLE_MAPS_API_KEY:
        # Fallback: use regular Google Maps link
        map_url = generate_google_maps_url(cities, use_embed=False)
        return f'<a href="{map_url}" target="_blank" style="display: block; padding: 10px; background: #f0f0f0; border-radius: 5px; text-decoration: none; color: #1976d2;">🗺️ View Trip Map ({len(cities)} places)</a>'
    
    embed_url = generate_google_maps_url(cities, use_embed=True)
    
    # Generate clickable map with link overlay
    map_url = generate_google_maps_url(cities, use_embed=False)
    
    # Extract place names for display
    place_names = [place.name if hasattr(place, "name") else str(place) for place in cities[:10]]
    
    html = f"""
    <div style="position: relative; width: {width}; height: {height}; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
        <iframe
            width="100%"
            height="100%"
            style="border:0;"
            loading="lazy"
            allowfullscreen
            referrerpolicy="no-referrer-when-downgrade"
            src="{embed_url}">
        </iframe>
        <a href="{map_url}" target="_blank" 
           style="position: absolute; bottom: 10px; right: 10px; background: white; padding: 8px 12px; border-radius: 4px; text-decoration: none; color: #1976d2; font-weight: 500; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
            Open in Google Maps →
        </a>
    </div>
    <p style="margin-top: 8px; font-size: 12px; color: #666;">
        Places: {', '.join(place_names)}
    </p>
    """
    
    return html

