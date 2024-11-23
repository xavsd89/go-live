import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import datetime

# Initialize Firebase using the credentials stored in Streamlit secrets
def initialize_firebase():
    # Load Firebase credentials from Streamlit secrets
    firebase_credentials = st.secrets["firebase_credentials"]
    cred_dict = json.loads(firebase_credentials)
    cred = credentials.Certificate(cred_dict)

    # Initialize the Firebase app (only if it's not already initialized)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)

    # Return a Firestore client
    return firestore.client()

# Firebase Firestore operation (e.g., insert project)
def insert_project_to_firestore(project_name, go_live_date):
    db = initialize_firebase()
    projects_ref = db.collection('projects')
    project_data = {
        "project_name": project_name,
        "go_live_date": go_live_date
    }
    projects_ref.add(project_data)

# Firebase Firestore operation (e.g., load projects)
def load_projects_from_firestore():
    db = initialize_firebase()
    projects_ref = db.collection('projects')
    docs = projects_ref.stream()
    projects = {}
    for doc in docs:
        project_data = doc.to_dict()
        project_name = project_data.get("project_name")
        go_live_date = project_data.get("go_live_date")
        projects[project_name] = go_live_date
    return projects

# Streamlit Page Setup
st.title("Project Management with Firebase")

# Dropdown to select project
projects = load_projects_from_firestore()

if projects:
    project_name = st.selectbox("Select a Project", list(projects.keys()))
    st.write(f"Go Live Date: {projects[project_name]}")

# Admin Page (for adding projects)
if st.button("Add Project"):
    project_name = st.text_input("Project Name")
    go_live_date = st.date_input("Go Live Date")
    
    if st.button("Submit"):
        if project_name and go_live_date:
            insert_project_to_firestore(project_name, go_live_date)
            st.success(f"Project '{project_name}' added successfully!")

# Admin login (for added security)
ADMIN_PASSWORD = "admin123"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Sidebar for admin password input
password = st.sidebar.text_input("Enter Admin Password", type="password")
if password == ADMIN_PASSWORD:
    st.session_state.is_admin = True
    st.sidebar.success("Logged in as Admin")
else:
    if password != "":
        st.sidebar.error("Invalid Password")

# Admin section to upload projects
if st.session_state.is_admin:
    st.sidebar.subheader("Upload Project Data")
    
    uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        # Process the uploaded Excel file
        import pandas as pd
        df = pd.read_excel(uploaded_file)
        if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
            st.sidebar.error('Excel must have "Project Name" and "Go Live Date" columns')
        else:
            for _, row in df.iterrows():
                project_name = row['Project Name']
                go_live_date = pd.to_datetime(row['Go Live Date']).strftime('%Y-%m-%d %H:%M:%S')
                insert_project_to_firestore(project_name, go_live_date)
            st.sidebar.success("Projects uploaded successfully")

# Display the available projects for countdown
if page == "Countdown":
    if 'projects' not in st.session_state:
        st.session_state.projects = load_projects_from_firestore()

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

# Template download (for first-time users)
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

st.sidebar.subheader("Download Excel Template")
template = generate_template()
st.sidebar.download_button("Download Template", data=template, file_name="template.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
