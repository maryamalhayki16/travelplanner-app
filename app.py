import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"

st.markdown(
    """
    <style>
    .stMarkdown p {
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<style>
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="AI Travel Planner", page_icon="✈️", layout="centered")

st.title("🗺️ Travel Planner")
st.markdown(
    "##### Sick of planning vacations? Create your perfect itinerary with AI!\n"
    "Get personalized recommendations for ***flights, hotels, and activities***"
)

if "results" not in st.session_state:
    st.session_state.results = None

# inputs
with st.container(border=True):    
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### ✈️ Flight Details")

        source = st.text_input("From (Airport Code)")
        arrival = st.text_input("To (Airport Code)")
        outbound_date = st.date_input("Outbound Date")
        return_date = st.date_input("Return Date")


    with col2:
        st.markdown("#### 🏨 Hotel Details")

        hotel_location = st.text_input("Hotel Location")

        auto_sync_dates = st.checkbox(
            "Match hotel dates with flight dates"
        )

        if auto_sync_dates:
            check_in = outbound_date
            check_out = return_date
            st.info("Hotel dates synced with flight dates ✨")
        else:
            check_in = st.date_input("Check-in Date")
            check_out = st.date_input("Check-out Date")

    with col3:
        st.markdown("#### 🎯 Preferences")

        destination = st.text_input("Destination City")
        budget = st.number_input("Budget", min_value=500)

        trip_type = st.selectbox(
            "Trip Type",
            ["Solo Trip", "Couple Getaway", "Family Vacation", "Friends Adventure"]
        )

        vibe = st.multiselect(
            "Interests",
            ["Exploring", "Historical", "Chill", "Adventure", "Sightseeing", "Nature"]
        )

def render_flights(flights):
    cols = st.columns(2)

    for i, flight in enumerate(flights):
        with cols[i % 2]:
            with st.container(border=True):

                segments = flight.get("segments", [])

                if segments:
                    origin_name = segments[0].get("from_name", "N/A")
                    destination_name = segments[-1].get("to_name", "N/A")
                    st.markdown(f"#### ✈︎ {origin_name} → {destination_name}")

                price = flight.get("price", "N/A")
                duration = flight.get("total_duration", "N/A")

                for seg in segments[:2]:
                    st.markdown(
                        f"🛫 **Departure:** {seg.get('from_name')} ({seg.get('from_id')}) at {seg.get('departure_time')}"
                    )
                    st.markdown(
                        f"🛬 **Arrival:** {seg.get('to_name')} ({seg.get('to_id')}) at {seg.get('arrival_time')}"
                    )
                    st.markdown(
                        f"🎫 **Airline:** {seg.get('airline')} ({seg.get('travel_class')})"
                    )

                st.markdown(f"⏱️ **Duration:** {duration} min")
                st.markdown(f"💰 **Price:** ${price}")

def render_hotels(hotels, cols_num=3):

    cols = st.columns(cols_num)

    for i, hotel in enumerate(hotels):
        with cols[i % cols_num]:
            with st.container(border=True):

                st.markdown(f"#### **🏨 {hotel.get('name', 'N/A')}**")

                price = hotel.get("price_per_night") or "N/A"
                rating = hotel.get("rating") or "N/A"
                Type = hotel.get("Type") or "N/A"

                st.markdown(f"📍 **Type:** {Type}")
                st.markdown(f"💰 **Price**: ${price} a Night")
                st.markdown(f"⭐ **Rating:** {rating}")

                amenities = hotel.get("amenities", [])

                if amenities:
                    st.markdown("🛎️ **Available Amenities:** " + ", ".join(amenities[:4]))
                else:
                    st.caption("No amenities listed")

if st.button("🚀 Generate My Trip"):

    if not source or not arrival or not destination:
        st.error("Fill all required fields.")
        st.stop()

    with st.spinner("Planning your trip..."):

        flight_payload = {
            "source": source,
            "destination": arrival,
            "outbound_date": str(outbound_date),
            "return_date": str(return_date)
        }

        hotel_payload = {
            "location": hotel_location if hotel_location else destination,
            "check_in_date": str(check_in),
            "check_out_date": str(check_out)
        }

        itinerary_payload = {
            "destination": destination,
            "check_in_date": str(check_in),
            "check_out_date": str(check_out),
            "budget": budget,
            "interests": vibe,
            "trip_type": trip_type
        }

        try:
            flights_res = requests.post(f"{BASE_URL}/search_flights/", json=flight_payload).json()
            hotels_res = requests.post(f"{BASE_URL}/search_hotels/", json=hotel_payload).json()

            itinerary_res = requests.post(
                f"{BASE_URL}/generate/itinerary",
                json={
                    "itinerary_request": itinerary_payload,
                    "flight_request": flight_payload,
                    "hotel_request": hotel_payload
                }
            ).json()
            

            st.session_state.results = {
                "flights": flights_res,
                "hotels": hotels_res,
                "itinerary": itinerary_res
            }

            st.toast("Trip generated successfully ✈️")

        except Exception as e:
            st.error(f"Something went wrong: {e}")



if st.session_state.results:

    results = st.session_state.results

    tab1, tab2, tab3, tab4 = st.tabs([
        "✈️ Flights",
        "🏨 Hotels",
        "👾 AI Recommendations",
        "🗺️ Itinerary"
    ])

# flights tab
    with tab1:
        st.markdown(f"#### ✈️ Available Flights from {source.upper()} to {arrival.upper()}")

        flights = results["flights"].get("flights", [])[:9]
        render_flights(flights)
                
                    

# hotels tab
    with tab2:
        st.markdown(f"#### 🏨 Available Hotels in {destination.upper()}")

        hotels = results["hotels"].get("hotels", [])[:9]
        render_hotels(hotels, 3)

# ai recommendations tab
    with tab3:
        st.markdown("### ✈️ Flight Recommendation")
        with st.container(border=True):
            st.markdown("### ✈️ Flight Recommendation")
            ai_flights = results["flights"].get("ai_flight_recommendation")
            st.markdown(ai_flights)

        st.markdown("### 🏨 Hotel Recommendation")
        with st.container(border=True):
            ai_hotels = results["hotels"].get("ai_hotel_recommendation")
            st.markdown(ai_hotels)


# itinerary tab
    with tab4:
        with st.container(border=True):
            itinerary = results["itinerary"].get("itinerary", "") or ""
            st.code(itinerary, language="markdown")
            st.download_button(
                "📥 Download TXT",
                itinerary,
                file_name=f"{destination} itinerary.txt",
                mime="text/plain"
            )