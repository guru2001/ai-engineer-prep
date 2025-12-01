"""Extract places from LLM trip planning responses using structured LLM output."""

from typing import List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    try:
        from langchain_core.pydantic_v1 import BaseModel, Field
    except ImportError:
        from pydantic.v1 import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


class Place(BaseModel):
    """Structured representation of a place with context."""
    name: str = Field(
        description="The name of the place (e.g., 'Eiffel Tower', 'Tokyo', 'Central Park')"
    )
    country: Optional[str] = Field(
        default=None,
        description="The country or region where this place is located (e.g., 'France', 'Japan', 'New York, USA'). Include this to help disambiguate places with common names."
    )
    type: Optional[str] = Field(
        default=None,
        description="The type of place (e.g., 'city', 'landmark', 'attraction', 'museum', 'park', 'neighborhood'). This helps with search accuracy."
    )
    context: Optional[str] = Field(
        default=None,
        description="Any additional context from the text that would help identify this specific place, such as nearby landmarks, district names, or distinguishing features."
    )


class PlaceList(BaseModel):
    """Structured output for place extraction."""
    places: List[Place] = Field(
        description="List of places mentioned in the trip itinerary. This can include cities, landmarks, attractions, and other destinations. Maximum 10 places. For each place, include the name and any available context (country, type, additional details) to improve search accuracy."
    )


def extract_places_from_text(text: str, model: Optional[ChatOpenAI] = None) -> List[Place]:
    """
    Extract up to 10 places from trip planning text using LLM with additional context.
    
    Args:
        text: The trip planning response text
        model: Optional ChatOpenAI model instance. If None, creates a new one.
    
    Returns:
        List of Place objects (up to 10) - each includes name, country, type, and context
    """
    if model is None:
        model = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    # Create structured output chain
    structured_llm = model.with_structured_output(PlaceList)
    
    # Prompt for place extraction with context
    system_prompt = (
        "You are a travel assistant that extracts places from trip planning text. "
        "Extract all relevant places that will be visited in the trip, including cities, landmarks, attractions, and other destinations. "
        "Include specific locations that are mentioned, such as famous landmarks, parks, museums, or neighborhoods. "
        "For each place, extract as much context as possible: the country/region it's in, the type of place, and any additional details "
        "that would help identify the exact location. This context is crucial for accurate geocoding and search results. "
        "Return a maximum of 10 places. If there are more than 10 places, return the first 10. "
        "Return an empty list if no places are found."
    )
    
    user_prompt = (
        f"Extract the places from the following trip planning text. "
        f"For each place, provide the name and any available context (country, type, additional details) that would help identify it accurately:\n\n{text}"
    )
    
    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        places = result.places[:10]  # Ensure max 10 places
        return places
    except Exception as e:
        # Fallback: return empty list if extraction fails
        print(f"Error extracting places: {e}")
        return []

