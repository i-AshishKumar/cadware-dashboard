import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from utils.data_processor import geocode_locations
from utils.data_processor import reduced_all_applications, num_immediate

st.set_page_config(layout="wide")
st.title('Cadware Dashboard')
# Color palette for consistency across charts
COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', '#D4A5A5', '#9B59B6']
st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Job Stats")
st.sidebar.page_link("pages/Mailing_list.py", label="Mailing list Stats")

tab1, tab2 = st.tabs(["Stats", "Trends"])
with tab1:
    # Job KPIs
    st.header("Job Application KPIs")
    total_applications = len(reduced_all_applications)
    female_applicants = len(reduced_all_applications[reduced_all_applications['gender']== 'Female'])
    male_applicants = len(reduced_all_applications[reduced_all_applications['gender']== 'Male'])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Applications", value= total_applications, delta=total_applications)
        st.metric(label="Applicants Available to Start Within a Week 🚨", value=num_immediate)
    with col2:
        st.metric(label="Female Applicants", value= female_applicants, delta=female_applicants)    
    with col3:
        st.metric(label="Male Applicants", value= male_applicants, delta=male_applicants)

    # Job Type Distribution (Pie)
    job_type_counts = reduced_all_applications['job_type'].value_counts().reset_index()
    job_type_counts.columns = ['job_type', 'count']

    st.header("Breakdown of Applicants by Job Type")
    pie_chart = alt.Chart(job_type_counts).mark_arc().encode(
        theta=alt.Theta('count:Q', title='Count'),
        color=alt.Color('job_type:N', scale=alt.Scale(range=COLORS), legend=alt.Legend(title='Job Type')),
        tooltip=['job_type', 'count']
    ).properties(
        width=400,
        height=400
    )
    st.altair_chart(pie_chart, use_container_width=True)


    # Prepare location strings
    reduced_all_applications['location'] = reduced_all_applications.apply(
        lambda row: f"{row['City']}, {row['State/Region']}, {row['Country']}".strip(', '),
        axis=1
    )

    # Convert unique locations to a tuple for cache stability
    unique_locations = tuple(reduced_all_applications['location'].unique())  # Tuple ensures hashable input

    # Geocode locations (cached)
    lat_lon_dict = geocode_locations(unique_locations)

    # Map lat/lon back to DataFrame
    reduced_all_applications['latitude'] = reduced_all_applications['location'].map(lambda x: lat_lon_dict.get(x, (None, None))[0])
    reduced_all_applications['longitude'] = reduced_all_applications['location'].map(lambda x: lat_lon_dict.get(x, (None, None))[1])

    # Drop rows with missing lat/lon
    df_map = reduced_all_applications.dropna(subset=['latitude', 'longitude'])

    # Display the map
    st.subheader("Geographic Map View of All Applicants")
    if not df_map.empty:
        st.map(df_map[['latitude', 'longitude']], zoom=1)
    else:
        st.warning("No valid locations found for mapping.")


with tab2:
    st.title("Top 3 Cities with Most Applicants")
    if reduced_all_applications.empty or 'City' not in reduced_all_applications.columns:
        st.error("Error: DataFrame is empty or 'City' column is missing.")
    else:
        # Get the top 3 cities with the most applicants and their counts
        city_counts = reduced_all_applications['City'].value_counts().head(3)
        top_cities = city_counts.index.tolist()
        counts = city_counts.values.tolist()

        # Display leaderboard
        if top_cities:
            for i, (city, count) in enumerate(zip(top_cities, counts), 1):
                # Use markdown for styled leaderboard entry
                st.markdown(
                    f"""
                    <div style='background-color: #f0f2f6; padding: 10px; margin: 5px; border-radius: 5px;'>
                        <span style='font-size: 1.2em; font-weight: bold;'>#{i}</span> 
                        <span style='font-size: 1.2em;'>{city}</span> 
                        <span style='color: #555;'>({count} applicants)</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.write("No data available.")

    st.markdown("\n\n\n")

    df = reduced_all_applications

    df['Earliest Available Date'] = pd.to_datetime(df['Earliest Available Date'], errors='coerce')
    df['Submission Date'] = pd.to_datetime(df['Submission Date'], errors='coerce')

    df['availability_days'] = (df['Earliest Available Date'] - df['Submission Date']).dt.days

    st.subheader('Days to availability Analysis')
    fig2 = px.box(df, x='job_type', y='availability_days', 
                labels={'job_type': 'Job Type', 'availability_days': 'Availability Days'},
                color='job_type')
    fig2.update_layout(xaxis_title='Job Type', yaxis_title='Availability in Days', 
                    xaxis_tickangle=45, showlegend=False)
    st.plotly_chart(fig2)










