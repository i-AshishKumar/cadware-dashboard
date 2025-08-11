import streamlit as st
import pandas as pd

st.sidebar.title("Navigation")
st.sidebar.page_link("app.py", label="Job Stats")
st.sidebar.page_link("pages/Mailing_list.py", label="Mailing list Stats")