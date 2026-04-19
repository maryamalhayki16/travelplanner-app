# AI Travel Planner
**An AI-powered travel planning application that recommends optimized flights, hotels, and itineraries based on user preferences.**

## Problem Statement
Planning a trip can be overwhelming due to the large number of flight and hotel options available across different platforms. Users often struggle to compare options efficiently and create a well-structured itinerary.

This project aims to simplify the travel planning process by using AI to:

- Analyze flight and hotel data
- Recommend the best options
- Generate a personalized travel itinerary

## Data Sources
The project uses flight and hotel data retrieved from APIs (SerpAPI), and user inputs to personalize the itinerary.

## Model Architecture
There are two main *components* for this project:\
**- AI Agents (CrewAI):** analyze and recommend the best flight and hotel options, and generate the itinerary.\
**- LLM (Google Gemini):** used for reasoning and recommendations, acting like the brain of the agents.

As for the *pipeline*, this approach was utilized:
1. **User inputs:** get the flight, hotel, and trip details from the user.
2. **Fetch Data:** API calls to retrieve real-time hotel and flight data.
3. **Clean/Format Data:** re-formatting the JSON structured data, handling missing values, and extracting relevant information.
4. **AI Agents Analysis:** agents recommend the top three flight and hotel options from the available data.
5. **Final Itinerary:** a full day-by-day travel itineray is generated.

## Evaluation Results
The main evaluation method is the **human-in-the-loop** method. Key success metrics with their results are:
- **Goal Achievement:** Did it work? -- agents work and complete their tasks.
- **Correctness and Relevance (1-5):** Is the agent's response accurate and useful for the user's objectives? -- 4, responses are accurate and fit the user's preferences.
- **Faithfulness (1-5):** Are the agent's outputs grounded in the tools and data it accessed? -- 4.5, the agent uses real data and executes relevant tools when necessary without hallucinations.
- **Cost and Latency (1-5):** Agent's resource usage, including API calls, tokens, and response time. -- 2, latency is ~5 minutes, and the responses are token-heavy.

## How to Run the Project?
To run the project:
1. Create a Virtual Environment and Activate It (Optional but Ideal):\
```bash
python -m venv venv
venv\Scripts\activate
```
2. Install Dependencies:\
`pip install -r requirements.txt`
3. Environment Variables Set-up:\
Create a .env file that contains your API keys:

```
ANTHROPIC_API_KEY = "INSERT YOUR KEY"
SERPAPI_API_KEY = "INSERT YOUR KEY"
EXA_API_KEY = "INSERT YOUR KEY"
GOOGLE_API_KEY = "INSERT YOUR KEY"
```
4- Run the backend server:\
`uvicorn main:app --reload`\
5- Run the app:\
`streamlit run app.py`

## Repository Structure
```
travelplanner-app/
│
├── app.py                # Main Streamlit app
├── main.py               # App logic and agents
├── requirements.txt      # Dependencies
├── .env                  # Environment variables (not pushed, but needs to be created)
└── README.md
```

## Limitations and Future Work
**Limitations**:
- Dependent on API availability and rate limits
- LLM responses may not always be perfectly accurate; prone to hallucinations
- Real-time pricing may fluctuate\
**Future Enhancements**:
- Add real-time booking integration
- Improve ranking algorithm
- Add user accounts & saved trips

## Demo Video
