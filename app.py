import streamlit as st
import requests
import json

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

# --- Location Input ---
st.markdown("### 📍 Enter Your Location")

city_name = st.text_input("🏙️ City Name (e.g., Bengaluru, Mumbai, Delhi, New York, Tokyo)", placeholder="Type your city name")

st.caption("— OR — Enter coordinates manually")

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", format="%.6f")
with col2:
    lon = st.number_input("Longitude", format="%.6f")

# --- Function to get coordinates from city name ---
def get_coordinates(city_name):
    if not city_name:
        return None, None
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        headers = {'User-Agent': 'SuryaNiti-Solar-Estimator'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except:
        pass
    return None, None

# --- If city name is entered, use it ---
if city_name:
    found_lat, found_lon = get_coordinates(city_name)
    if found_lat and found_lon:
        lat = found_lat
        lon = found_lon
        st.success(f"📍 Found: {city_name} (Lat: {lat:.4f}, Lon: {lon:.4f})")

# --- Function to check if location is in India ---
def is_in_india(lat, lon):
    """Check if coordinates are within India's approximate bounding box"""
    # India approximate bounds: 8°N to 37°N, 68°E to 97°E
    if 8.0 <= lat <= 37.0 and 68.0 <= lon <= 97.0:
        return True
    return False

# --- Function to fetch NASA data ---
def fetch_nasa_data(lat, lon):
    """Fetch solar radiation data from NASA POWER API"""
    
    url = f"https://power.larc.nasa.gov/api/temporal/climatology/point?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={lon}&latitude={lat}&format=JSON"
    
    try:
        response = requests.get(url, timeout=30)
        
        if response.status_code != 200:
            return None, f"NASA API returned status: {response.status_code}"
        
        data = response.json()
        
        param_data = data.get('properties', {}).get('parameter', {}).get('ALLSKY_SFC_SW_DWN', {})
        
        if not param_data:
            return None, "No radiation data found for this location"
        
        values = [v for v in param_data.values() if isinstance(v, (int, float))]
        
        if not values:
            return None, "No valid data values found"
        
        avg_daily = sum(values) / len(values)
        return avg_daily, None
        
    except Exception as e:
        return None, str(e)

# --- Function to get Gemini AI Recommendations ---

def get_gemini_recommendations(solar_data, api_key, is_india):
    """Get personalized recommendations from Google Gemini"""
    
    location_type = "in India" if is_india else "outside India"
    
    # Build the prompt lines conditionally
    prompt_lines = [
        "You are an expert solar energy consultant.",
        f"Based on this analysis for a household {location_type}:",
        f"- Average Solar Radiation: {solar_data['avg_daily']:.2f} kWh/m²/day",
        f"- Recommended System Size: {solar_data['system_kw']:.1f} kW",
        f"- Annual Generation: {solar_data['potential_kwh']:,.0f} kWh",
        f"- Monthly Savings: {solar_data['currency']}{solar_data['monthly_savings']:,.0f}",
    ]
    
    # Add subsidy line only if in India
    if is_india and solar_data['subsidy'] is not None:
        prompt_lines.append(f"- PM Surya Ghar Subsidy: {solar_data['currency']}{solar_data['subsidy']:,.0f}")
    
    prompt_lines.append("")
    prompt_lines.append("Provide:")
    prompt_lines.append("1. A brief overall assessment of this household's solar potential (1 sentence).")
    prompt_lines.append("2. 3 specific, actionable recommendations for the homeowner.")
    
    # Add tip about PM Surya Ghar only if in India
    if is_india:
        prompt_lines.append("3. A quick tip about the PM Surya Ghar scheme.")
    else:
        prompt_lines.append("3. General next steps for adopting solar.")
    
    prompt_lines.append("")
    prompt_lines.append("Keep the tone friendly, encouraging, and practical. Write in simple English.")
    prompt_lines.append("Format each point on a new line with clear numbering.")
    
    prompt = "\n".join(prompt_lines)
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code != 200:
            error_data = response.json()
            error_msg = error_data.get('error', {}).get('message', 'Unknown error')
            return None, f"API Error: {error_msg}"
        
        data = response.json()
        
        if 'candidates' in data and len(data['candidates']) > 0:
            candidate = data['candidates'][0]
            if 'content' in candidate and 'parts' in candidate['content']:
                text = candidate['content']['parts'][0]['text']
                return text, None
        
        return None, "No response from Gemini AI"
        
    except Exception as e:
        return None, str(e)

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
        
        # --- 2. Check if location is in India ---
        in_india = is_in_india(lat, lon)
        
        # --- 3. Calculations ---
        panel_efficiency = 0.20
        roof_area_sqm = 46.45
        
        annual_radiation = avg_daily * 365
        potential_kwh = annual_radiation * roof_area_sqm * panel_efficiency
        system_kw = potential_kwh / (365 * 5)
        
        # --- Set currency and rates based on location ---
        if in_india:
            currency = "₹"
            electricity_rate = 7.0
            # PM Surya Ghar Subsidy calculation (India only)
            if system_kw <= 3:
                subsidy = system_kw * 30000
            elif system_kw <= 10:
                subsidy = 90000 + (system_kw - 3) * 18000
            else:
                subsidy = system_kw * 18000
        else:
            currency = "$"
            electricity_rate = 0.12  # Approximate US rate
            subsidy = None  # No subsidy for non-India locations
        
        monthly_savings = (potential_kwh / 12) * electricity_rate
        
        solar_data = {
            'avg_daily': avg_daily,
            'system_kw': system_kw,
            'potential_kwh': potential_kwh,
            'monthly_savings': monthly_savings,
            'subsidy': subsidy,
            'currency': currency,
            'in_india': in_india
        }
        
        # --- 4. Display Results ---
        st.success("✅ Solar Analysis Complete!")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("☀️ Solar Radiation", f"{avg_daily:.2f} kWh/m²/day")
        with col2:
            st.metric("⚡ System Capacity", f"{system_kw:.1f} kW")
        with col3:
            st.metric("🔋 Annual Generation", f"{potential_kwh:,.0f} kWh")
        with col4:
            st.metric("💰 Monthly Savings", f"{currency}{monthly_savings:,.0f}")
        
        # Show subsidy ONLY if in India
        if in_india and subsidy is not None:
            st.metric("🏛️ PM Surya Ghar Subsidy", f"{currency}{subsidy:,.0f}")
        else:
            st.info("ℹ️ PM Surya Ghar subsidy is available only for locations in India.")
        
        # --- 5. Get Gemini AI Recommendations ---
        with st.spinner("🧠 Asking Gemini AI for personalized recommendations..."):
            
            ai_text, ai_error = get_gemini_recommendations(solar_data, api_key, in_india)
            
            st.divider()
            st.markdown("### 💡 AI-Powered Recommendations")
            
            if ai_text:
                st.success(ai_text)
                st.caption("🤖 Generated by Google Gemini AI")
            else:
                st.warning(f"⚠️ AI recommendations are temporarily unavailable: {ai_error}")
                
                # --- FALLBACK RECOMMENDATIONS ---
                st.info("📋 **Here are some general recommendations based on your data:**")
                
                if system_kw > 5:
                    st.write(f"✅ **Excellent potential!** Your {system_kw:.1f} kW system can cover most of your electricity needs.")
                    st.write("📌 **Next steps:**")
                    st.write("1. Contact 3 verified solar installers for quotes")
                    if in_india:
                        st.write(f"2. Apply for PM Surya Ghar subsidy ({currency}{subsidy:,.0f})")
                    st.write("3. Schedule a site assessment")
                elif system_kw > 3:
                    st.write(f"👍 **Good potential!** A {system_kw:.1f} kW system will significantly reduce your electricity bills.")
                    st.write("📌 **Next steps:**")
                    st.write("1. Check for any shading on your rooftop")
                    st.write("2. Get quotes from multiple installers")
                    if in_india:
                        st.write(f"3. Apply for PM Surya Ghar subsidy ({currency}{subsidy:,.0f})")
                else:
                    st.write(f"ℹ️ Your {system_kw:.1f} kW potential is moderate.")
                    st.write("📌 **Suggestions:**")
                    st.write("1. Consider optimizing roof space usage")
                    st.write("2. Explore ground-mounted options if available")
                    st.write("3. Consult with a solar expert for personalized advice")

# --- Footer ---
st.divider()
st.caption("🚀 Built for India AI Impact Festival 2026 | Data: NASA POWER | AI: Google Gemini")
st.caption("📍 Works for any location globally. PM Surya Ghar subsidy displayed only for India.")
