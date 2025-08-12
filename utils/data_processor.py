import pandas as pd
from pathlib import Path
import re
import streamlit as st
import time
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

job_apps_dir = Path("Application/")

csv_files = list(job_apps_dir.rglob("*.csv"))

dfs = {}
for file in csv_files:
    # Extract the job type from the csv filename
    job_type = file.stem.split("-application")[0] 
    
    df = pd.read_csv(file)
    df["job_type"] = job_type  # add new column
    
    dfs[file.stem.split("-application")[0]] = df
job_apps_types = list(dfs.keys())
all_applications = pd.concat(dfs[x] for x in job_apps_types)

reduced_all_applications = all_applications.drop(columns = ['User Id', 'Notes', 'Submission Admin View URL', 'Submitter IP', 'Submitter Browser', 'Submitter Device', 'Submission ID', 'Submission Serial Number', 'Source URL', 'Submission Status'])

gender_map = {
    "Mr": "Male",
    "Mrs": "Female",
    "Miss": "Female"
}

reduced_all_applications["gender"] = reduced_all_applications["Title"].map(gender_map)

reduced_all_applications.drop('Title',axis=1, inplace=True)


def extract_country(address):
    if pd.isna(address):
        return None
    match = re.search(r'\((.*?)\)$', address.strip())
    if match:
        return match.group(1)
    return address.split(',')[-1].strip()

def extract_city(address):
    if pd.isna(address):
        return None
    parts = address.split(',')
    return parts[0].strip()

def extract_state(address):
    if pd.isna(address):
        return None
    parts = address.split(',')
    if len(parts) > 2:
        return parts[1].strip()
    elif len(parts) == 2:
        # Only city and country
        return None
    return None

# Function to geocode locations with persistent caching
@st.cache_data(persist=True)  # Persist cache to disk for reuse across sessions
def geocode_locations(unique_locations_tuple, _cache_key="geocode_cache"):
    geolocator = Nominatim(user_agent="cadware_dash")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=2, error_wait_seconds = 10)
    lat_lon = {}
    for loc in unique_locations_tuple:
        try:
            location = geocode(loc)
            if location:
                lat_lon[loc] = (location.latitude, location.longitude)
            else:
                lat_lon[loc] = (None, None)
        except Exception as e:
            st.warning(f"Error geocoding {loc}: {e}")
            lat_lon[loc] = (None, None)
            time.sleep(1)
    return lat_lon

reduced_all_applications["Country"] = reduced_all_applications["Address"].apply(extract_country)
reduced_all_applications["City"] = reduced_all_applications["Address"].apply(extract_city)
reduced_all_applications["State/Region"] = reduced_all_applications["Address"].apply(extract_state)


reduced_all_applications.rename(columns={"What is your earliest available date": "Earliest Available Date"}, inplace=True)
reduced_all_applications.rename(columns={"Submission Create Date": "Submission Date"}, inplace=True)

reduced_all_applications['Earliest Available Date'] = pd.to_datetime(reduced_all_applications['Earliest Available Date'])

reduced_all_applications["Available_DayOfWeek"] = reduced_all_applications["Earliest Available Date"].dt.day_name()
reduced_all_applications["Available_Month"] = reduced_all_applications["Earliest Available Date"].dt.month_name()
reduced_all_applications["Available_Year"] = reduced_all_applications["Earliest Available Date"].dt.year


# Ensure 'Submission Date' is in datetime format
reduced_all_applications['Submission Date'] = pd.to_datetime(reduced_all_applications['Submission Date'])

# Extract year, month (as full name), day
reduced_all_applications['submit_year'] = reduced_all_applications['Submission Date'].dt.year
reduced_all_applications['submit_month'] = reduced_all_applications['Submission Date'].dt.strftime('%B')
reduced_all_applications['submit_day'] = reduced_all_applications['Submission Date'].dt.day

# Define function to categorize time of day
def categorize_time_of_day(hour):
    if 0 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 18:
        return 'Afternoon'
    else:
        return 'Evening'

# Extract hour and apply time of day categorization
reduced_all_applications['submit_time_of_day'] = reduced_all_applications['Submission Date'].dt.hour.apply(categorize_time_of_day)


reduced_all_applications['Earliest Available Date'] = pd.to_datetime(reduced_all_applications['Earliest Available Date'], errors='coerce')
reduced_all_applications['Submission Date'] = pd.to_datetime(reduced_all_applications['Submission Date'], errors='coerce')

# Drop rows with invalid dates
temp = reduced_all_applications
immediate_candidates = temp.dropna(subset=['Earliest Available Date', 'Submission Date'])

# Filter for candidates available within 10 days of submission
immediate_candidates = immediate_candidates[
    immediate_candidates['Earliest Available Date'] <= immediate_candidates['Submission Date'] + pd.Timedelta(days=7)
]

num_immediate = len(immediate_candidates)