import streamlit as st
import pandas as pd
import plotly.express as px
import geoip2.database
import requests
import time


st.set_page_config(page_title="Mailing List Insights", layout="wide")

st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Job Stats")
st.sidebar.page_link("pages/Mailing_list.py", label="Mailing list Stats")

# -------------------
# Load Data
# -------------------


st.title("📊 Mailing List Insights Dashboard")

@st.cache_data
def load_data():
    df = pd.read_csv("Join Mailing List/join-our-mailing-list-2025-07-21.csv")
    df['Submission Create Date'] = pd.to_datetime(df['Submission Create Date'])
    return df

df = load_data()


# -------------------
# Count sign-ups per source
# -------------------
source_counts = df['How did you hear about us?'].value_counts().reset_index()
source_counts.columns = ['Source', 'Count']
total_count = source_counts['Count'].sum()

# -------------------
# Display Metrics in a Grid
# -------------------
cols = st.columns(4)  # 4 metrics per row

for idx, row in source_counts.iterrows():
    col = cols[idx % 4]
    source = row['Source']
    count = row['Count']
    percent = round((count / total_count) * 100, 1)
    
    col.metric(label=source, value=count, delta=f"{percent}% of total")

    if (idx + 1) % 4 == 0:
        st.write("")

# -------------------
# Optional: Geolocate IPs (requires GeoLite2 database)
# -------------------
@st.cache_data
def geolocate(df):
    try:
        reader = geoip2.database.Reader('utils/assets/GeoLite2-City.mmdb')
    except FileNotFoundError:
        st.warning("GeoLite2 database not found. Skipping geolocation.")
        df['Country'] = None
        df['City'] = None
        return df

    countries = []
    cities = []

    def fallback_api(ip):
        try:
            res = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city", timeout=5).json()
            if res.get("status") == "success":
                return res.get("country"), res.get("city")
            else:
                return None, None
        except:
            return None, None

    for ip in df['Submitter IP']:
        try:
            response = reader.city(ip)
            country = response.country.name
            city = response.city.name
            if not country or not city:
                # fallback if missing info
                country, city = fallback_api(ip)
        except:
            country, city = fallback_api(ip)

        countries.append(country)
        cities.append(city)
        # to be polite with public API limits
        time.sleep(0.1)  # 100ms pause

    df['Country'] = countries
    df['City'] = cities

    reader.close()
    return df

df = geolocate(df)

# -------------------
# Filters
# -------------------
channels = st.multiselect("Channel", options=df['How did you hear about us?'].unique(), default=df['How did you hear about us?'].unique())
date_range = st.date_input("Date Range", [df['Submission Create Date'].min(), df['Submission Create Date'].max()])

filtered_df = df[
    (df['How did you hear about us?'].isin(channels)) &
    (df['Submission Create Date'].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
]

# -------------------
# Channel Performance
# -------------------
st.subheader("Sign-ups by Channel Over Time")
channel_time = filtered_df.groupby([pd.Grouper(key='Submission Create Date', freq='D'), 'How did you hear about us?']).size().reset_index(name='Count')
fig1 = px.line(channel_time, x='Submission Create Date', y='Count', color='How did you hear about us?', markers=True)
st.plotly_chart(fig1, use_container_width=True)

# -------------------
# Device Distribution
# -------------------
st.subheader("Device Type Distribution")
fig2 = px.pie(filtered_df, names='Submitter Device', title='Device Share')
st.plotly_chart(fig2, use_container_width=True)

# -------------------
# Hourly Pattern
# -------------------
st.subheader("Hourly Sign-up Patterns")
filtered_df['Hour'] = filtered_df['Submission Create Date'].dt.hour
hourly = filtered_df.groupby('Hour').size().reset_index(name='Count')
fig3 = px.bar(hourly, x='Hour', y='Count', title="Sign-ups by Hour of Day")
st.plotly_chart(fig3, use_container_width=True)

# -------------------
# Geographic Map
# -------------------

# Load GeoJSON for countries (Natural Earth or similar)
geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
geojson = requests.get(geojson_url).json()

# Prepare data: country_counts is your DataFrame with 'Country' and 'Count'

# Make sure your country names in country_counts match those in geojson['features'][].properties.name
# You might need to map names to standard ones, e.g., "United States" vs "USA"
country_counts = df.groupby('Country').size().reset_index(name='Count')
country_counts['Country'] = country_counts['Country'].replace({
    "United States": "United States of America",
    "Russia": "Russian Federation",
    "South Korea": "Korea, Republic of",
    # Add other mappings if needed
})

# Create the map
fig4 = px.choropleth_mapbox(
    country_counts,
    geojson=geojson,
    locations='Country',          # column in your DataFrame
    featureidkey='properties.name',  # path to country name in GeoJSON
    color='Count',
    color_continuous_scale="Viridis",
    mapbox_style="open-street-map",
    zoom=1,
    center={"lat": 20, "lon": 0},
    opacity=0.6,
    hover_name='Country'
)

st.plotly_chart(fig4, use_container_width=True)


# -------------------
# Channel vs Device Heatmap
# -------------------
st.subheader("Channel vs Device")
heatmap_data = filtered_df.groupby(['How did you hear about us?', 'Submitter Device']).size().reset_index(name='Count')
fig5 = px.density_heatmap(heatmap_data, x="How did you hear about us?", y="Submitter Device", z="Count", color_continuous_scale="Blues")
st.plotly_chart(fig5, use_container_width=True)

# -------------------
# Raw Data Preview
# -------------------
with st.expander("View Raw Data"):
    st.dataframe(filtered_df)
