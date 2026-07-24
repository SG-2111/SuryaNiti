import streamlit as st
import requests
import os
from datetime import datetime, timedelta


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


st.markdown("### 📍 Enter Your Location")

col1, col2 = st.columns(2)
with col1:
    lat = st.number_input("Latitude", value=12.9716, format="%.6f", help="e.g., 12.9716 for Bengaluru")
with col2:
    lon = st.number_input("Longitude", value=77.5946, format="%.6f", help="e.g., 77.5946 for Bengaluru")

st.caption("📍 Default location: Bengaluru. Change to your city.")


if st.button("🔍 Analyze with Gemini AI", type="primary"):
    
    with st.spinner("🌍 Fetching solar data from NASA satellites..."):
        
        # --- 1. Get NASA POWER Data ---
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=ALLSKY_SFC_SW_DWN&latitude={lat}&longitude={lon}&start={start_date.strftime('%Y%m%d')}&end={end_date.strftime('%Y%m%d')}&format=JSON"
        
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            
            daily_values = list(data['properties']['parameter']['ALLSKY_SFC_SW_DWN'].values())
            avg_daily = sum(daily_values) / len(daily_values)
            
        except Exception as e:
            st.error(f"❌ Failed to fetch NASA data: {str(e)}")
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
                Based on this analysis for a household:
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
                gemini_response = requests.post(gemini_url, json=payload)
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


st.divider()
st.caption("🚀 Built for India AI Impact Festival 2026 | Data: NASA POWER | AI: Google Gemini")
st.caption("📡 Solar data sourced from NASA POWER satellite observations")
