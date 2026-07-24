import streamlit as st
import requests
import json
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="SuryaShakti", layout="centered")

st.title("☀️ SuryaShakti")
st.subheader("AI-Powered Solar Potential Estimator for India")
st.markdown("Get personalized solar recommendations using real NASA data and Google Gemini AI.")

# --- Get API Key from Streamlit Secrets ---
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.error("⚠️ Gemini API key not found. Please set GEMINI_API_KEY in Streamlit Cloud secrets.")
    st.info("Go to your app dashboard → Settings → Secrets")
    st.stop()

# --- Location Input ---
st.markdown("### 📍 Enter Your Location")

# Option 1: Type a city name
city_name = st.text_input("🏙️ City Name (e.g., Bengaluru, Mumbai, Delhi)", placeholder="Type your city name")

# Option 2: Manual coordinates
st.caption("— OR — Enter coordinates manually")

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", value=12.9716, format="%.6f")
with col2:
    lon = st.number_input("Longitude", value=77.5946, format="%.6f")

# --- Function to get coordinates from city name ---
def get_coordinates(city_name):
    """Get latitude and longitude from city name"""
    if not city_name:
        return None, None
    
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name},India&format=json&limit=1"
        headers = {'User-Agent': 'SuryaShakti-Solar-Estimator'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
    except Exception as e:
        st.warning(f"Could not find city: {city_name}. Please enter coordinates manually.")
    
    return None, None

# --- If city name is entered, use it ---
if city_name:
    found_lat, found_lon = get_coordinates(city_name)
    if found_lat and found_lon:
        lat = found_lat
        lon = found_lon
        st.success(f"📍 Found: {city_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")

# --- Function to fetch NASA data (using the correct API) ---
def fetch_nasa_data(lat, lon):
    """Fetch solar radiation data from NASA POWER API"""
    
    # Using the correct NASA POWER API endpoint
    # This endpoint returns monthly climatology data (always available)
    url = f"https://power.larc.nasa.gov/api/power/v2/point?parameters=ALLSKY_SFC_SW_DWN&latitude={lat}&longitude={lon}&format=JSON&user=anonymous"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            return None, f"NASA API returned status: {response.status_code}"
        
        data = response.json()
        
        # Extract the solar radiation values
        # The data structure is: properties -> parameter -> ALLSKY_SFC_SW_DWN
        radiation_data = data.get('properties', {}).get('parameter', {}).get('ALLSKY_SFC_SW_DWN', {})
        
        if not radiation_data:
            return None, "No radiation data found for this location"
        
        # Get all values from the monthly data
        daily_values = []
        for month, value in radiation_data.items():
            if isinstance(value, (int, float)):
                daily_values.append(value)
        
        if not daily_values:
            return None, "No valid data values found"
        
        # Calculate average daily radiation
        avg_daily = sum(daily_values) / len(daily_values)
        
        return avg_daily, None
        
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return None, "Network error. Please check your internet connection."
    except Exception as e:
        return None, f"Error: {str(e)}"

# --- Analyze Button ---
if st.button("🔍 Analyze with Gemini AI", type="primary"):
    
    with st.spinner("🌍 Fetching solar data from NASA satellites..."):
        
        # --- 1. Get NASA Data ---
        avg_daily, error = fetch_nasa_data(lat, lon)
        
        if error:
            st.error(f"❌ Failed to fetch NASA data: {error}")
            st.info("💡 Try using a different location or check your internet connection.")
            st.stop()
        
        if avg_daily is None:
            st.error("❌ No data available for this location.")
            st.stop()
        
        # --- 2. Calculations ---
        panel_efficiency = 0.20
        roof_area_sqm = 46.45  # 500 sq ft
        
        annual_radiation = avg_daily * 365
        potential_kwh = annual_radiation * roof_area_sqm * panel_efficiency
        system_kw = potential_kwh / (365 * 5)
        monthly_savings = (potential_kwh / 12) * 7.0  # ₹7 per kWh
        
        # PM Surya Ghar Subsidy calculation
        if system_kw <= 3:
            subsidy = system_kw * 30000
        elif system_kw <= 10:
            subsidy = 90000 + (system_kw - 3) * 18000
        else:
            subsidy = system_kw * 18000
        
        # --- 3. Display Results ---
        st.success("✅ Solar Analysis Complete!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("☀️ Solar Radiation", f"{avg_daily:.2f} kWh/m²/day")
        with col2:
            st.metric("⚡ System Capacity", f"{system_kw:.1f} kW")
        with col3:
            st.metric("🔋 Annual Generation", f"{potential_kwh:,.0f} kWh")
        with col4:
            st.metric("💰 Monthly Savings", f"₹{monthly_savings:,.0f}")
        
        st.metric("🏛️ PM Surya Ghar Subsidy", f"₹{subsidy:,.0f}")
        
        # --- 4. Get Gemini AI Recommendations ---
        with st.spinner("🧠 Asking Gemini AI for personalized recommendations..."):
            
            prompt = f"""
                You are an expert solar energy consultant for India.
                Based on this analysis for a household at coordinates ({lat:.4f}, {lon:.4f}):
                - Average Solar Radiation: {avg_daily:.2f} kWh/m²/day
                - Recommended System Size: {system_kw:.1f} kW
                - Annual Generation: {potential_kwh:,.0f} kWh
                - Monthly Savings: ₹{monthly_savings:,.0f}
                - PM Surya Ghar Subsidy: ₹{subsidy:,.0f}
                
                Provide:
                1. A brief overall assessment of this household's solar potential.
                2. 3 specific, actionable recommendations for the homeowner.
                3. A quick tip about the PM Surya Ghar scheme.
                
                Keep the tone friendly, encouraging, and practical. Write in simple English.
            """
            
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            try:
                gemini_response = requests.post(gemini_url, json=payload, timeout=30)
                result = gemini_response.json()
                
                if 'candidates' in result:
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    
                    st.divider()
                    st.markdown("### 💡 AI-Powered Recommendations")
                    st.success(ai_response)
                else:
                    st.warning("⚠️ AI recommendations are temporarily unavailable.")
                    
            except Exception as e:
                st.error(f"❌ AI Error: {str(e)}")

# --- Footer ---
st.divider()
st.caption("🚀 Built for India AI Impact Festival 2026 | Data: NASA POWER | AI: Google Gemini")