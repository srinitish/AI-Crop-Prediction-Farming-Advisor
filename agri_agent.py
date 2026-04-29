import joblib
from typing import TypedDict
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
from langgraph.graph import StateGraph
model = joblib.load("crop_prediction_model.pkl")

load_dotenv()


llm = ChatGroq(
    model = "llama-3.3-70b-versatile",
    temperature=0.7,
    api_key= os.getenv("GORQ_API")
)

def predict_crop(data):
    prediction = model.predict([[
        data["N"],
        data["P"],
        data["K"],
        data["temperature"],
        data["humidity"],
        data["ph"],
        data["rainfall"]
    ]])

    return prediction[0]

import requests

def get_location(place):

    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": place,
        "format": "json",
        "limit": 1
    }

    headers = {
        "User-Agent": "agri-agent-project"
    }

    response = requests.get(url, params=params, headers=headers)

    print(response.text)   # debug

    data = response.json()

    if len(data) == 0:
        return None

    return {
        "latitude": float(data[0]["lat"]),
        "longitude": float(data[0]["lon"])
    }




def get_weather(latitude, longitude):

    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,precipitation"

    response = requests.get(url)
    data = response.json()

    return {
        "temperature": data["current"]["temperature_2m"],
        "humidity": data["current"]["relative_humidity_2m"],
        "rainfall": data["current"]["precipitation"]   # precipitation = rainfall in mm
    }



class GraphAgent(TypedDict):
    soil_data: dict
    location: dict
    predict_crop: str
    weather: dict
    advice: str

generate_advice_template = PromptTemplate(
    input_variables=["crop", "weather","soil"],
    template= """
You are a Senior Agronomist and Precision Agriculture Specialist.

### CONTEXT DATA
- **Target Crop:** {crop}
- **Real-time Weather:** {weather}
- **Soil Profile (NPK/pH):** {soil}

### GOAL
Provide a high-yield "Prescription Plan" for the farmer. Focus on advanced techniques like Evapotranspiration scheduling, nutrient bioavailability, and stress management that traditional methods often overlook.

### CONSTRAINTS
- Be scientifically precise but practically actionable.
- Use imperative verbs (e.g., "Adjust," "Apply," "Monitor").
- **NO** introductory filler ("As an expert...", "Here is...").
- Max 6 bullet points.

### REQUIRED STRUCTURE
1. **Irrigation Strategy:** Based on current humidity/temp, define the watering depth or timing.
2. **Nutrient Optimization:** Suggest adjustments to N-P-K uptake based on current soil pH.
3. **Environmental Adaptation:** One specific action to mitigate current weather risks (e.g., heat stress, leaching).
4. **The "Secret" Edge:** One expert-level tip (like Controlled Deficit Irrigation or specific microbial focus).

Output as a clean, numbered list.
"""
)


def get_weather_agent(GraphAgent: dict) -> dict:
    location = GraphAgent["location"]

    weather = get_weather(location["latitude"], location["longitude"])

    GraphAgent["weather"] = weather

    GraphAgent["soil_data"]["temperature"] = weather["temperature"]
    GraphAgent["soil_data"]["humidity"] = weather["humidity"]
    GraphAgent["soil_data"]["rainfall"] = weather["rainfall"]
    return GraphAgent

def soil_data_agent(GraphAgent: dict) -> dict:
    soil_data = GraphAgent["soil_data"]
    prediction = predict_crop(soil_data)
    GraphAgent["predict_crop"] = prediction
    return GraphAgent




def advice_agent(GraphAgent: dict) -> dict:
    crop = GraphAgent["predict_crop"]
    weather = GraphAgent["weather"]
    soil = GraphAgent["soil_data"]
    prompt = generate_advice_template.format(crop=crop, weather=weather, soil=soil)
    advice = llm.invoke(prompt)
    GraphAgent["advice"] = advice.content
    return GraphAgent

graph = StateGraph(GraphAgent)

graph.add_node("weather_agent", get_weather_agent)
graph.add_node("soil_data_agent", soil_data_agent)
graph.add_node("advice_agent", advice_agent)

graph.set_entry_point("weather_agent")
graph.add_edge("weather_agent", "soil_data_agent")
graph.add_edge("soil_data_agent", "advice_agent") 
app = graph.compile()




if __name__ == "__main__":
    initial_data = {
        "soil_data": {
            "N": 90,
            "P": 42,
            "K": 43,
            "temperature": 20,
            "humidity": 80,
            "ph": 6.5,
            "rainfall": 200
        },
        "location": {
            "latitude": 41.2994,
            "longitude": -95.9233
        }
    }
    result = app.invoke(initial_data)
    print(result["advice"])