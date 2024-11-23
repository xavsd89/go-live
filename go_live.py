import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import datetime
import time
from io import BytesIO

# Firebase setup
cred = credentials.Certificate("path_to_your_service_account_key.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://your-database-name.firebaseio.com/'
})

# Firebase reference
projects_ref = db.reference('projects')

ADMIN_PASSWORD = "admin123"

# Insert project into Firebase Realtime Database
def insert_project(project_name, go_live_date):
    project_ref = projects_ref.child(project_name)
    project_ref.set({
        'project_name': project_name,
        'go_live_date': go_live_date
    })

# Delete project from Firebase Realtime Database
def delete_project(project_name):
    project_ref = projects_ref.child(project_name)
    project_ref.delete()

# Load all projects from Firebase
def load_projects():
    projects = projects_ref.get()
    if projects:
        return {project_name: datetime.datetime.strptime(project_data['go_live_date'], '%Y-%m-%d %H:%M:%S') 
                for project_name, project_data in projects.items()}
    else:
        return {}

# Handle Excel upload
def upload_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
        st.error('Excel must have "Project Name" and "Go Live Date" columns')
        return
    
    for _, row in df.iterrows():
        project_name = row['Project Name']
        go_live_date = pd.to_datetime(row['Go Live Date']).strftime('%Y-%m-%d %H:%M:%S')
        insert_project(project_name, go_live_date)
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

# Initialize Firebase if needed
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Set session state for admin
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Sidebar page selection
page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])

# Countdown Page
if page == "Countdown":
    if 'projects' not in st.session_state:
        st.session_state.projects = load_projects()

    projects = st.session_state.projects

    if projects:
        project = st.selectbox("Select a project", list(projects.keys()))

        def get_time_left(go_live):
            return go_live - datetime.datetime.now()

        st.write(f"Go Live date for {project}: {projects[project]:%Y-%m-%d %H:%M:%S}")

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
            st.session_state.projects = load_projects()

        projects = st.session_state.projects
        if projects:
            project_to_delete = st.sidebar.selectbox("Delete Project", list(projects.keys()))
            if st.sidebar.button("Delete"):
                delete_project(project_to_delete)
                st.session_state.projects = load_projects()
                st.sidebar.success(f"Deleted {project_to_delete}")

        st.sidebar.subheader("Download Excel Template")
        template = generate_template()
        st.sidebar.download_button("Download Template", data=template, file_name="template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.sidebar.write("Please log in to manage projects.")
