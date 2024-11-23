import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import sqlite3
import datetime
import time
from io import BytesIO

# Firebase setup from Streamlit Secrets
cred_dict = st.secrets["firebase"]
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()

ADMIN_PASSWORD = "admin123"

# Drop the existing projects collection in Firestore (if needed)
def drop_firestore_collection():
    projects_ref = db.collection("projects")
    docs = projects_ref.stream()
    for doc in docs:
        doc.reference.delete()

# Create the Firestore collection for storing project details
def create_firestore_collection():
    projects_ref = db.collection("projects")
    # Optionally, create a test entry to check if it works
    projects_ref.add({
        "project_name": "Test Project",
        "go_live_date": datetime.datetime.now()
    })

# Insert project into Firestore
def insert_project_firestore(project_name, go_live_date):
    projects_ref = db.collection("projects")
    projects_ref.add({
        "project_name": project_name,
        "go_live_date": go_live_date
    })

# Load all projects from Firestore
def load_projects_firestore():
    projects_ref = db.collection("projects")
    docs = projects_ref.stream()
    projects = {doc.id: doc.to_dict()["go_live_date"] for doc in docs}
    return projects

# Handle Excel upload
def upload_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
        st.error('Excel must have "Project Name" and "Go Live Date" columns')
        return
     
    for _, row in df.iterrows():
        project_name = row['Project Name']
        go_live_date = pd.to_datetime(row['Go Live Date'])
        insert_project_firestore(project_name, go_live_date)
    st.success('Projects uploaded')

# Generate an Excel template for first-time users
def generate_template():
    data = {
        'Project Name': ['Project A', 'Project B'],
        'Go Live Date': ['2024-12-01 12:00:00', '2024-12-15 15:00:00']
    }
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return buffer

# Initialize Firestore if it doesn't exist
drop_firestore_collection()
create_firestore_collection()

# Set session state for admin
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Sidebar page selection
page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])

# Countdown Page
if page == "Countdown":
    if 'projects' not in st.session_state:
        st.session_state.projects = load_projects_firestore()

    projects = st.session_state.projects

    if projects:
        project = st.selectbox("Select a project", list(projects.keys()))

        def get_time_left(go_live):
            return go_live - datetime.datetime.now()

        st.write(f"Go Live date for {project}: {projects[project]}")

        countdown_placeholder = st.empty()

        while True:
            time_left = get_time_left(projects[project])
            if time_left > datetime.timedelta(0):
                days_left = time_left.days
                hours_left, remainder = divmod(time_left.seconds, 3600)
                minutes_left, seconds_left = divmod(remainder, 60)

                # Full spelling without commas, singular/plural handled
                days_text = f"{days_left} day{'s' if days_left != 1 else ''}"
                hours_text = f"{hours_left} hour{'s' if hours_left != 1 else ''}"
                minutes_text = f"{minutes_left} minute{'s' if minutes_left != 1 else ''}"
                seconds_text = f"{seconds_left} second{'s' if seconds_left != 1 else ''}"

                # Concatenating all parts with spaces instead of commas
                countdown_text = f"{days_text} {hours_text} {minutes_text} {seconds_text}"

                countdown_placeholder.markdown(f"### {countdown_text}")
            else:
                countdown_placeholder.markdown("### The Go Live event is NOW!")

            time.sleep(1)
    else:
        st.write("No projects in the database. Upload some!")

# Admin Page
elif page == "Setup (Admin only)":
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.session_state.is_admin = True
        st.sidebar.success("Logged in as Admin")
        
        uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
        if uploaded_file:
            upload_file(uploaded_file)
            st.session_state.projects = load_projects_firestore()

        projects = st.session_state.projects
        if projects:
            project_to_delete = st.sidebar.selectbox("Delete Project", list(projects.keys()))
            if st.sidebar.button("Delete"):
                # Add code for deleting project from Firestore
                pass

        st.sidebar.subheader("Download Excel Template")
        template = generate_template()
        st.sidebar.download_button("Download Template", data=template, file_name="template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.sidebar.write("Please log in to manage projects.")
