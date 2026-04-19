import logging 
import os
import json
from datetime import datetime
from functools import lru_cache
import asyncio
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel
#from langchain_anthropic import ChatAnthropic
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import EXASearchTool
from fastapi import FastAPI, HTTPException
import serpapi

load_dotenv() # load env 

SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY') 
client = serpapi.Client(api_key=SERPAPI_API_KEY)

exa_tool = EXASearchTool() # search tool

# logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title='Travel Planner', version='1.0') # initializing a rest api

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

@lru_cache(maxsize=1)
def initialize_llm(): # initialize and cache the llm, using claude
    return LLM(
    model="gemini-2.5-flash",
    provider="google",
    api_key=GOOGLE_API_KEY
    )


# data validation
class FlightRequest(BaseModel):
    source: str
    destination: str
    outbound_date: str
    return_date: str
class HotelRequest(BaseModel):
    location: str
    check_in_date: str
    check_out_date: str
class FlightInfo(BaseModel):
    segments: list
    total_duration: Optional[int]
    price: Optional[float]
class HotelInfo(BaseModel):
    name: str
    Type: str | None = None
    price_per_night: float | None = None
    total_price: float | None = None
    rating: float | None = None
    amenities: list | None = None
class ItineraryRequest(BaseModel):
    destination: str
    check_in_date: str
    check_out_date: str
    budget: float
    interests: list
    trip_type: str
class AIResponse(BaseModel):
    flights: List[FlightInfo] = []
    hotels: List[HotelInfo] = []
    ai_flight_recommendation: str = ""
    ai_hotel_recommendation: str = ""
    itinerary: str = ""


# ### test
# flight_request = {
#     'source': 'jfk',
#     'destination': 'aus',
#     'outbound_date': "2026-06-01",
#     'return_date': "2026-06-15"
# }

# hotel_request = {
#     'location': 'bahrain',
#     'check_in_date': '2026-06-01',
#     'check_out_date': '2026-06-15'
# }

async def run_search(params): # global function to run SerpAPI searches
    try:
        return await asyncio.to_thread(lambda: client.search(params).as_dict())
    except Exception as e:
        logger.exception(f'SerpAPI search error: {str(e)}')
        raise HTTPException(status_code=500, detail=f'Search API error: {str(e)}')

async def search_flights(flight_request: FlightRequest): # search for flights using serpapi
    logger.info(f'Searching flights: {flight_request.source} to {flight_request.destination}')

    params = {
    "api_key" : SERPAPI_API_KEY,
    "engine" : "google_flights",
    "departure_id" : flight_request.source.strip().upper(), 
    "arrival_id" : flight_request.destination.strip().upper(), 
    "outbound_date" : flight_request.outbound_date, 
    "return_date" : flight_request.return_date 
    }

    search_results = await run_search(params)
    flights_raw = search_results

    return flights_raw

async def search_hotels(hotel_request: HotelRequest): # search for hotels using serpapi
    logger.info(f'Searching hotels for {hotel_request.location}')

    params = {
    "api_key" : SERPAPI_API_KEY,
    "engine" : "google_hotels",
    "q" : hotel_request.location,
    "check_in_date" : hotel_request.check_in_date,
    "check_out_date" : hotel_request.check_out_date
    }

    search_results = await run_search(params)
    hotels_raw = search_results

    return hotels_raw



def extract_flights(flights_raw): # extracting formatted flights data from API response
    formatted_flights = []
    keys = ['best_flights', 'other_flights']

    for key in keys:
        for item in flights_raw.get(key, []):
            segments = []

            for flight in item.get('flights', []):
                segments.append({
                    'from_id': flight.get('departure_airport', {}).get('id'),
                    'from_name': flight.get('departure_airport', {}).get('name'),
                    'to_id': flight.get('arrival_airport', {}).get('id'),
                    'to_name': flight.get('arrival_airport', {}).get('name'),
                    'departure_time': flight.get('departure_airport', {}).get('time'),
                    'arrival_time': flight.get('arrival_airport', {}).get('time'),
                    'airline': flight.get('airline'),
                    'travel_class' : flight.get('travel_class')
                })

            formatted_flights.append({
                'segments': segments,
                'total_duration': item.get('total_duration'),
                'price': item.get('price')
            })

    return formatted_flights

def extract_hotels(hotels_raw, limit=30): # extracting formatted hotels data from API response
    formatted_hotels = []

    for hotel in hotels_raw.get("properties", [])[:limit]:
        amenities = hotel.get('amenities') or []
        formatted_hotels.append({
            "name": hotel.get("name"),
            "Type": hotel.get("type"),
            "price_per_night": hotel.get("rate_per_night", {}).get("extracted_lowest"),
            "total_price": hotel.get("total_rate", {}).get("extracted_lowest"),
            "rating": hotel.get("overall_rating"),
            "amenities": amenities[:5]
        })

    return formatted_hotels

async def ai_flight_recommendation(formatted_flights):
    logger.info('Getting flight analysis from AI')
    llm = initialize_llm() # defining the brain of our agents
    
    description = """
                From the provided data, select the top 3 flights.

                Return ONLY the top 3 flights in this exact format:

                1. Route: <from → to>
                Price: <price>
                Duration: <duration>
                Stops: <number of stops>

                2. Route: ...
                Price: ...
                Duration: ...
                Stops: ...

                3. Route: ...
                Price: ...
                Duration: ...
                Stops: ...

                Rules:
                - No explanations
                - No extra text
                - No markdown headers
                - Only the 3 items above
                """
    # create flight agent
    flight_agent = Agent(
        role = 'Flight Analyst',
        goal = 'Analyze flight options and recommend the best three options considering price, duration, stops, and overall convenience.',
        backstory = 'You are an expert who provides an in-depth analysis comparing flight options based on multiple factors.',
        description = description,
        llm = llm,
        verbose = False
    )
    # agent's task
    flight_task = Task(
        description = f"""
        {description},
        Data:
        {formatted_flights}
        """,
        agent = flight_agent,
        expected_output = ''''A list of the top three best flights, following this structure for each flight:
        1. Route: <from → to>
        Price: <price>
        Duration: <duration>
        Stops: <number of stops>
        with the Route, Price, Duration, and Stops tags being in bold.
        '''
    )
    # CrewAI workflow
    flight_crew = Crew(
        agents=[flight_agent],
        tasks=[flight_task],
        process=Process.sequential,
        verbose=False
    )

    crew_results = await asyncio.to_thread(flight_crew.kickoff)
    return str(crew_results)

async def ai_hotel_recommendation(formatted_hotels):
    logger.info('Getting flight analysis from AI')
    llm = initialize_llm() # defining the brain of our agents

    description = """
                Select the top 3 hotels.

                Return ONLY in this format:

                1. Name: <name>
                Price: <price per night>
                Rating: <rating>
                Type: <type>

                2. Name: ...
                Price: ...
                Rating: ...
                Type: ...

                3. Name: ...
                Price: ...
                Rating: ...
                Type: ...

                Rules:
                - No explanations
                - No extra text
                - No markdown
                """
    # create hotel agent
    hotel_agent = Agent(
        role = 'Hotel Analyst',
        goal = 'Analyze hotel options and recommend the best option considering price, rating, location, and amenities.',
        backstory = 'You are an expert who provides an in-depth analysis comparing hotel options based on multiple factors.',
        description = description,
        llm = llm, 
        verbose = False
    )
    # agent's task
    hotel_task = Task(
        description = f'{description}\n\nData to Analyze: {formatted_hotels}',
        agent = hotel_agent,
        expected_output = '''A list of the top three hotels, following this structure for each hotel:
        1. <hotel's name>
        Price: <price per night>
        Rating: <rating>
        Type: <type>
        with the name, price, rating, and type tags in bold.
        '''
    )
    # CrewAI workflow
    hotel_crew = Crew(
        agents=[hotel_agent],
        tasks=[hotel_task],
        process=Process.sequential,
        verbose=False
    )

    crew_results = await asyncio.to_thread(hotel_crew.kickoff)
    return str(crew_results)

async def generate_itinerary(destination, formatted_flights, formatted_hotels, check_in_date, check_out_date, budget, interests, trip_type):
    
    check_in = datetime.strptime(check_in_date, '%Y-%m-%d')
    check_out = datetime.strptime(check_out_date, '%Y-%m-%d')
    days = (check_out - check_in).days

    llm = initialize_llm()

    itinerary_agent = Agent(
        role="Travel Itinerary Planner",
        goal="Create a personalized, realistic travel itinerary using real-world activities",
        backstory="""
        You are an expert travel planner who builds detailed itineraries.
        You ALWAYS use web search to find real attractions, restaurants, and experiences.
        You optimize plans based on budget, vibe, and trip type.
        """,
        tools=[exa_tool],
        llm=llm,
        verbose=True
    )

    itinerary_task = Task(
        description=f"""
        Based on the following details, create a {days}-day itinerary for the user:

        **Flights Details**:
        {formatted_flights}

        **Hotels Details**:
        {formatted_hotels}

        **Destination**: {destination}

        **Travel Dates**: {check_in_date} to {check_out_date} ({days} days)

        Keep in mind user's preferences: {interests} 
        And the trip type of {trip_type}
        Without exceeding the total budget {budget}

        The itinerary should include:
            - Flight arrival and departure information
            - Hotel check-in and check-out details
            - Day-by-day breakdown of activities
            - Must-visit attractions and estimated visit times
            - Restaurant recommendations for meals
            - Tips for local transportation

            **Format Requirements**:
            - Use markdown formatting with clear headings (# for main headings, ## for days, ### for sections)
            - Include emojis for different types of activities ( for landmarks, 🍽️ for restaurants, etc.)
            - Use bullet points for listing activities
            - Include estimated timings for each activity
            - Format the itinerary to be visually appealing and easy to read

        """,
        agent=itinerary_agent,
        expected_output="A well-structured, visually appealing itinerary in markdown format, including flight, hotel, and day-wise breakdown with emojis, headers, and bullet points."
    )

    itinerary_planner_crew = Crew(
        agents=[itinerary_agent],
        tasks=[itinerary_task],
        process=Process.sequential,
        verbose=False
    )

    crew_results = await asyncio.to_thread(itinerary_planner_crew.kickoff)
    return str(crew_results)

# API Endpoints
@app.post("/search_flights/", response_model=AIResponse)
async def get_flight_recommendation(flight_request: FlightRequest):
    flights_raw = await search_flights(flight_request)
    flights_clean = extract_flights(flights_raw)
    flights_formatted = []
    for f in flights_clean:
        try:
            flights_formatted.append(FlightInfo(**f))
        except Exception as e:
            logger.warning(f"Skipping invalid flight {f} | error: {e}")
    ai_recommendation = await ai_flight_recommendation(flights_formatted)
    return AIResponse(flights=flights_formatted, ai_flight_recommendation=ai_recommendation)

@app.post("/search_hotels/", response_model=AIResponse)
async def get_hotel_recommendation(hotel_request: HotelRequest):
    hotels_raw = await search_hotels(hotel_request)
    hotels_clean = extract_hotels(hotels_raw)
    hotels_formatted = [HotelInfo(**h) for h in hotels_clean]
    ai_recommendation = await ai_hotel_recommendation(hotels_formatted)
    return AIResponse(hotels=hotels_formatted, ai_hotel_recommendation=ai_recommendation)

@app.post("/generate/itinerary", response_model=AIResponse)
async def get_itinerary(itinerary_request: ItineraryRequest, flight_request: FlightRequest, hotel_request: HotelRequest):

    flights_raw = await search_flights(flight_request)
    hotels_raw = await search_hotels(hotel_request)

    flights = extract_flights(flights_raw)
    hotels = extract_hotels(hotels_raw)

    flights = [FlightInfo(**f) for f in flights]
    hotels = [HotelInfo(**h) for h in hotels]

    ai_flights = await ai_flight_recommendation(flights)
    ai_hotels = await ai_hotel_recommendation(hotels)

    itinerary = await generate_itinerary(
        itinerary_request.destination,
        ai_flights,
        ai_hotels,
        itinerary_request.check_in_date,
        itinerary_request.check_out_date,
        itinerary_request.budget,
        itinerary_request.interests,
        itinerary_request.trip_type
    )
    return AIResponse(
        itinerary=itinerary
    )
