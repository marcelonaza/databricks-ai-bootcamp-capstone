"""Streamlit frontend for the Weather Intelligence Databricks App."""
from __future__ import annotations
import pandas as pd
import requests
import streamlit as st

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
WMO = {0:("Clear sky","☀️"),1:("Mainly clear","🌤️"),2:("Partly cloudy","⛅"),3:("Overcast","☁️"),45:("Fog","🌫️"),48:("Rime fog","🌫️"),51:("Light drizzle","🌦️"),53:("Drizzle","🌦️"),55:("Dense drizzle","🌧️"),61:("Slight rain","🌦️"),63:("Moderate rain","🌧️"),65:("Heavy rain","🌧️"),71:("Slight snow","🌨️"),73:("Snow","❄️"),75:("Heavy snow","❄️"),80:("Rain showers","🌦️"),81:("Rain showers","🌧️"),82:("Heavy showers","⛈️"),85:("Snow showers","🌨️"),86:("Heavy snow showers","❄️"),95:("Thunderstorm","⛈️"),96:("Thunderstorm with hail","⛈️"),99:("Severe thunderstorm","⛈️")}

class WeatherUIError(RuntimeError):
    pass

def get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise WeatherUIError("Weather data is temporarily unavailable. Try again shortly.") from exc
    if not isinstance(payload, dict) or payload.get("error"):
        raise WeatherUIError(str(payload.get("reason", "Unexpected weather response.")))
    return payload

@st.cache_data(ttl=900, show_spinner=False)
def load_weather(location, days):
    geocode = get_json(GEOCODING_URL, {"name":location.strip(),"count":1,"language":"en","format":"json"})
    matches = geocode.get("results") or []
    if not matches:
        raise WeatherUIError("Location not found. Add a country or region and try again.")
    place = matches[0]
    label = ", ".join(str(v) for v in (place.get("name"),place.get("admin1"),place.get("country")) if v)
    result = get_json(FORECAST_URL, {
        "latitude":place["latitude"],"longitude":place["longitude"],
        "current":"temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
        "daily":"weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max,uv_index_max",
        "forecast_days":days,"timezone":"auto"})
    return {"location":label,"current":result["current"],"daily":result["daily"]}

def describe(code):
    return WMO.get(int(code),("Unknown conditions","🌡️"))

def recommendations(day):
    advice=[]
    if (day["Rain chance (%)"] or 0)>=40: advice.append("☂️ Bring an umbrella or waterproof layer.")
    if day["Low (°C)"]<12: advice.append("🧥 Bring a jacket for the colder part of the day.")
    if (day["UV index"] or 0)>=6: advice.append("🧴 Use sunscreen and seek shade around midday.")
    if (day["Wind (km/h)"] or 0)>=40: advice.append("💨 Use caution with exposed outdoor activities.")
    return advice or ["✅ No special precautions are indicated by the weather rules."]

st.set_page_config(page_title="Naza Weather Intelligence",page_icon="🌦️",layout="wide")
st.markdown("""<style>.block-container{max-width:1180px;padding-top:2rem}[data-testid="stMetric"]{background:#111827;border:1px solid #263244;padding:1rem;border-radius:14px}.hero{padding:1.5rem 1.75rem;border-radius:18px;background:linear-gradient(120deg,#10243e,#164e63);margin-bottom:1.25rem}.hero h1{margin:0;color:#f8fafc}.hero p{margin:.4rem 0 0;color:#cbd5e1}</style><div class="hero"><h1>🌦️ Naza Weather Intelligence</h1><p>Live conditions, multi-day forecasts and explainable outdoor recommendations.</p></div>""",unsafe_allow_html=True)
with st.sidebar:
    st.header("Weather search")
    location=st.text_input("Location",value="Lisbon, Portugal",help="Include country for ambiguous cities.")
    days=st.slider("Forecast days",1,7,3)
    search=st.button("Analyze weather",type="primary",use_container_width=True)
    st.divider()
    st.caption("Powered by Open-Meteo. No API key or stored personal data.")
if search or "weather" not in st.session_state:
    if len(location.strip())<2:
        st.warning("Enter at least two characters."); st.stop()
    try:
        with st.spinner("Loading live weather data..."): st.session_state.weather=load_weather(location,days)
    except WeatherUIError as exc:
        st.error(str(exc)); st.stop()
data=st.session_state.weather
current=data["current"]
conditions,icon=describe(current["weather_code"])
st.subheader(f"{icon} {data['location']}")
st.caption(f"Observed at {current.get('time','latest available time')}")
columns=st.columns(5)
for col,label,value in zip(columns,["Temperature","Feels like","Humidity","Wind","Conditions"],[f"{current['temperature_2m']:.1f} °C",f"{current['apparent_temperature']:.1f} °C",f"{current['relative_humidity_2m']}%",f"{current['wind_speed_10m']:.1f} km/h",conditions]):
    col.metric(label,value)
daily=data["daily"]; rows=[]
for i,day in enumerate(daily["time"]):
    description,symbol=describe(daily["weather_code"][i])
    rows.append({"Date":day,"Conditions":f"{symbol} {description}","High (°C)":daily["temperature_2m_max"][i],"Low (°C)":daily["temperature_2m_min"][i],"Rain chance (%)":daily["precipitation_probability_max"][i],"Rain (mm)":daily["precipitation_sum"][i],"Wind (km/h)":daily["wind_speed_10m_max"][i],"UV index":daily["uv_index_max"][i]})
frame=pd.DataFrame(rows)
forecast_tab,advice_tab,about_tab=st.tabs(["Forecast","Recommendations","About"])
with forecast_tab:
    st.dataframe(frame,hide_index=True,use_container_width=True)
    st.line_chart(frame.set_index("Date")[["High (°C)","Low (°C)"]],color=["#f59e0b","#38bdf8"])
with advice_tab:
    selected=st.selectbox("Recommendation date",frame["Date"].tolist())
    chosen=frame.loc[frame["Date"]==selected].iloc[0].to_dict()
    for item in recommendations(chosen): st.info(item)
    st.caption("Rules: umbrella at ≥40% rain; jacket below 12 °C; sun protection at UV ≥6; wind caution at ≥40 km/h.")
with about_tab:
    st.markdown("This frontend complements the Databricks Weather Agent and its custom MCP server. The agent uses three MCP tools for current conditions, forecasts and derived recommendations.")
    st.warning("Forecasts can change. For severe weather, consult official local authorities.")
st.caption("Data source: Open-Meteo · Educational project")
