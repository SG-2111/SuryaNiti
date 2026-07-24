import streamlit as st
import requests
import os
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="SuryaNiti", layout="centered")

st.title("☀️ SuryaNiti")
st.subheader("AI-Powered Solar Potential Estimator for India")
st.markdown("Get personalized solar recommendations using real NASA data and Google Gemini AI.")

# --- Get API Key from Streamlit Secrets ---
api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.error("⚠️ Gemini API key not found. Please set GEMINI_API_KEY in Streamlit Cloud secrets.")
    st.info("Go to your app dashboard → Settings → Secrets")
    st.stop()

# --- Location Input (Two Ways) ---
st.markdown("### 📍 Enter Your Location")

# Option 1: Type a city name
city_name = st.text_input("🏙️ City Name (e.g., Bengaluru, Mumbai, Delhi)", placeholder="Type your city name")

# Option 2: Manual coordinates
st.caption("— OR — Enter coordinates manually")

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", value=12.9716, format="%.6f", help="e.g., 12.9716 for Bengaluru")
with col2:
    lon = st.number_input("Longitude", value=77.5946, format="%.6f", help="e.g., 77.5946 for Bengaluru")

# --- Function to get coordinates from city name (using free Nominatim API) ---
def get_coordinates(city_name):
    """Get latitude and longitude from city name using OpenStreetMap Nominatim API"""
    if not city_name:
        return None, None
    
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name},India&format=json&limit=1"
        headers = {'User-Agent': 'SuryaNiti Solar Estimator'}
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

# --- Analyze Button ---
if st.button("🔍 Analyze with Gemini AI", type="primary"):
    
    with st.spinner("🌍 Fetching solar data from NASA satellites..."):
        
        # --- 1. Get NASA POWER Data (Using Climatology - More Stable) ---
        try:
            # Use climatology data (monthly averages over many years) - always available
            url = f"https://power.larc.nasa.gov/api/power/v2/point?parameters=ALLSKY_SFC_SW_DWN&latitude={lat}&longitude={lon}&format=JSON&user=anonymous"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                st.error(f"❌ NASA API error: {response.status_code}")
                st.stop()
            
            data = response.json()
            
            # Extract daily average radiation from climatology data
            daily_values = []
            for month_data in data['properties']['parameter']['ALLSKY_SFC_SW_DWN']:
                daily_values.extend(month_data['values'])
            
            avg_daily = sum(daily_values) / len(daily_values)
            
        except Exception as e:
            st.error(f"❌ Failed to fetch NASA data: {str(e)}")
            st.info("💡 Please check your internet connection or try again later.")
            st.stop()
        
        # --- 2. Calculations ---
        panel_efficiency = 0.20  # 20% efficient panels
        roof_area_sqm = 46.45    # 500 sq ft
        
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
                Based on this analysis for a household at coordinates ({lat}, {lon}):
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
                    st.info(ai_response)
                else:
                    st.warning("⚠️ AI recommendations are temporarily unavailable.")
                    
            except Exception as e:
                st.error(f"❌ AI Error: {str(e)}")

# --- Footer ---
st.divider()
st.caption("🚀 Built for India AI Impact Festival 2026 | Data: NASA POWER | AI: Google Gemini")
st.caption("📡 Solar data sourced from NASA POWER satellite observations")