import streamlit as st
import pandas as pd
import requests
from streamlit_js_eval import get_geolocation
from agri_agent import app

st.set_page_config(page_title="AI Crop Advisor", layout="wide")

st.title("🌱 AI Crop Prediction & Farming Advisor")
st.write("Predict the best crop and get AI farming advice.")

# -------------------------
# SIDEBAR SOIL INPUTS
# -------------------------

st.sidebar.header("Enter Soil Data")

N = st.sidebar.number_input("Nitrogen (N)", 0, 200, 90)
P = st.sidebar.number_input("Phosphorus (P)", 0, 200, 42)
K = st.sidebar.number_input("Potassium (K)", 0, 200, 43)

ph = st.sidebar.number_input("Soil pH", 0.0, 14.0, 6.5)

# -------------------------
# LOCATION BUTTON
# -------------------------

col1, col2 = st.columns([3,1])

with col1:
    track = st.button("📍 Track My Location")

if track:
    loc = get_geolocation()

    if loc and "coords" in loc:
        lat = loc["coords"]["latitude"]
        lon = loc["coords"]["longitude"]

        st.session_state["lat"] = lat
        st.session_state["lon"] = lon

        # Reverse geocode
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        headers = {"User-Agent": "agri-ai-app"}

        response = requests.get(url, headers=headers)
        data = response.json()

        address = data.get("display_name", "Location detected")

        st.session_state["address"] = address

    else:
        st.error("Location permission required. Please allow location access.")

# -------------------------
# DISPLAY MAP
# -------------------------

with col2:

    if "lat" in st.session_state:

        map_data = pd.DataFrame({
            "lat":[st.session_state["lat"]],
            "lon":[st.session_state["lon"]]
        })

        st.map(map_data, zoom=10)

        st.caption(st.session_state.get("address",""))

# -------------------------
# PREDICTION BUTTON
# -------------------------

st.subheader("Run Crop Prediction")

if st.button("Predict Crop & Get Advice"):

    if "lat" not in st.session_state:
        st.error("Please click 'Track My Location' first.")
        st.stop()

    with st.spinner("Running AI Agents..."):

        initial_data = {
            "soil_data": {
                "N": N,
                "P": P,
                "K": K,
                "ph": ph,
            },
            "location": {
                "latitude": st.session_state["lat"],
                "longitude": st.session_state["lon"]
            }
        }

        result = app.invoke(initial_data)

        crop = result["predict_crop"]
        weather = result["weather"]
        advice = result["advice"]

    st.success("Prediction Completed")

    # -------------------------
    # OUTPUT
    # -------------------------

    st.subheader("🌱 Predicted Crop")
    st.write(crop)

    st.subheader("🌤 Current Weather")

    c1, c2, c3 = st.columns(3)

    c1.metric("Temperature", f"{weather['temperature']} °C")
    c2.metric("Humidity", f"{weather['humidity']} %")
    c3.metric("Rainfall", f"{weather['rainfall']} mm")

    st.subheader("🤖 AI Advice")

    advice_lines = advice.split("\n")

    for line in advice_lines:
        if line.strip():
            st.write(f"• {line}")