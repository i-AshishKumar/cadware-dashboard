import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt
from utils.data_processor import geocode_locations  # Ensure this function is defined in your utils
from utils.data_processor import reduced_all_applications, num_immediate

st.set_page_config(layout="wide")
st.title('📊 Cadware Jobs Dashboard')
# Color palette for consistency across charts
COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEEAD', '#D4A5A5', '#9B59B6']
st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Job Stats")
st.sidebar.page_link("pages/Mailing_list.py", label="Mailing list Stats")

# Geocode all unique locations upfront (before filtering)
# Create location strings for the full dataset
reduced_all_applications['location'] = reduced_all_applications.apply(
    lambda row: f"{row['City']}, {row['State/Region']}, {row['Country']}".strip(', '),
    axis=1
)
unique_locations = tuple(reduced_all_applications['location'].unique())  # Tuple for cache stability
lat_lon_dict = geocode_locations(unique_locations)  # Cache this result

tab1, tab2 = st.tabs(["Stats", "Trends"])
with tab1:
    st.header("Job Application KPIs")

    # Get unique job types for filtering
    unique_job_types = sorted(reduced_all_applications['job_type'].unique())

    # Multiselect widget for filtering job types (default to all)
    selected_job_types = st.multiselect(
        'Filter by Job Types',
        options=unique_job_types,
        default=unique_job_types,
        key='job_type_filter_tab1'
    )

    # Filter the DataFrame based on selected job types
    filtered_df = reduced_all_applications[reduced_all_applications['job_type'].isin(selected_job_types)]

    total_applications = len(filtered_df)
    female_applicants = len(filtered_df[filtered_df['gender'] == 'Female'])
    male_applicants = len(filtered_df[filtered_df['gender'] == 'Male'])

    # Calculate most sought out job title with tie-breaker (alphabetical)




    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Total Applications", value=total_applications, delta=total_applications)
        st.metric(label="Applicants Available to Start Within a Week 🚨", value=len(filtered_df[(filtered_df['Earliest Available Date'] - filtered_df['Submission Date']).dt.days <= 7]))
    with col2:
        st.metric(label="Female Applicants", value=female_applicants, delta=female_applicants)
        job_counts = filtered_df['job_type'].value_counts()

        if not job_counts.empty:
            max_count = job_counts.max()
            tied_jobs = job_counts[job_counts == max_count].index.tolist()
            most_sought_job = sorted(tied_jobs)[0].replace("-", " ").title()  # alphabetically first among ties
            st.metric(label="Popular Job Title", value=most_sought_job)
        else:
            st.metric(label="Popular Job Title", value="N/A", delta=None)    
    with col3:
        st.metric(label="Male Applicants", value=male_applicants, delta=male_applicants)

    # Job Type Distribution (Pie)
    job_type_counts = filtered_df['job_type'].value_counts().reset_index()
    job_type_counts.columns = ['job_type', 'count']

    if not job_type_counts.empty:
        pie_chart = alt.Chart(job_type_counts).mark_arc().encode(
            theta=alt.Theta('count:Q', title='Count'),
            color=alt.Color('job_type:N', scale=alt.Scale(range=COLORS), legend=alt.Legend(title='Job Type')),
            tooltip=['job_type', 'count']
        ).properties(
            width=400,
            height=400
        )
        st.altair_chart(pie_chart, use_container_width=True)
    else:
        st.info("Please select at least one job type to view the breakdown.")

    # Map lat/lon back to filtered DataFrame using cached results
    filtered_df['latitude'] = filtered_df['location'].map(lambda x: lat_lon_dict.get(x, (None, None))[0])
    filtered_df['longitude'] = filtered_df['location'].map(lambda x: lat_lon_dict.get(x, (None, None))[1])

    # Drop rows with missing lat/lon
    df_map = filtered_df.dropna(subset=['latitude', 'longitude'])

    # Display the map
    st.header("Geolocation of Applicants")
    if not df_map.empty:
        st.map(df_map[['latitude', 'longitude']], zoom=1)
    else:
        st.warning("No valid locations found for mapping.")

# Rest of your code for tab2 remains unchanged
with tab2:
    st.header("Top 3 Cities with Most Applicants")
    if reduced_all_applications.empty or 'City' not in reduced_all_applications.columns:
        st.error("Error: DataFrame is empty or 'City' column is missing.")
    else:
        city_counts = reduced_all_applications['City'].value_counts().head(3)
        top_cities = city_counts.index.tolist()
        counts = city_counts.values.tolist()

        if top_cities:
            # Define colors for 1st, 2nd, and 3rd place
            rank_colors = ['#FFE066', '#D9D9D9', '#E0A875']  # Gold, Silver, Bronze
            for i, (city, count) in enumerate(zip(top_cities, counts), 1):
                # Use the corresponding color based on rank
                bg_color = rank_colors[i-1] if i <= len(rank_colors) else '#f0f2f6'  # Fallback color
                st.markdown(
                    f"""
                    <div style='background-color: {bg_color}; padding: 10px; margin: 5px; border-radius: 5px;'>
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


    st.header('Monthly job listing performance')

    unique_job_types = sorted(df['job_type'].unique())
    selected_job_types = st.multiselect(
        'Select Job Types to Display',
        options=unique_job_types,
        default=unique_job_types
    )

    filtered_df = df[df['job_type'].isin(selected_job_types)]
    agg_df = filtered_df.groupby(['submit_month', 'job_type']).size().reset_index(name='Application Count')

    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                'July', 'August', 'September', 'October', 'November', 'December']
    agg_df['submit_month'] = pd.Categorical(agg_df['submit_month'], categories=month_order, ordered=True)
    agg_df = agg_df.sort_values(['submit_month', 'job_type'])

    if not agg_df.empty:
        fig = px.bar(
            agg_df,
            x='submit_month',
            y='Application Count',
            color='job_type',
            barmode='group',
            labels={'submit_month': 'Month of Submission', 'Application Count': 'Number of Applications', 'job_type': 'Job Type'}
        )
        fig.update_layout(
            xaxis_title='Month of Submission',
            yaxis_title='Number of Applications',
            legend_title='Job Type',
            xaxis_tickangle=45,
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write('No data available for the selected job types.')

    st.markdown("\n\n\n")



    df['Earliest Available Date'] = pd.to_datetime(df['Earliest Available Date'], errors='coerce')
    df['Submission Date'] = pd.to_datetime(df['Submission Date'], errors='coerce')

    df['availability_days'] = (df['Earliest Available Date'] - df['Submission Date']).dt.days

    st.header('Days to Availability Analysis')
    fig2 = px.box(df, x='job_type', y='availability_days', 
                labels={'job_type': 'Job Type', 'availability_days': 'Availability Days'},
                color='job_type')
    fig2.update_layout(xaxis_title='Job Type', yaxis_title='Availability in Days', 
                    xaxis_tickangle=45, showlegend=False)
    st.plotly_chart(fig2)

    df = reduced_all_applications

    df['Submission Date'] = pd.to_datetime(df['Submission Date'], errors='coerce')
    df = df.dropna(subset=['submit_month', 'job_type'])

