import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import datetime

# Initialize Firebase app
if not firebase_admin._apps:
    cred = credentials.Certificate({
        "type": st.secrets["firebase_credentials"]["type"],
        "project_id": st.secrets["firebase_credentials"]["project_id"],
        "private_key_id": st.secrets["firebase_credentials"]["private_key_id"],
        "private_key": st.secrets["firebase_credentials"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase_credentials"]["client_email"],
        "client_id": st.secrets["firebase_credentials"]["client_id"],
        "auth_uri": st.secrets["firebase_credentials"]["auth_uri"],
        "token_uri": st.secrets["firebase_credentials"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase_credentials"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase_credentials"]["client_x509_cert_url"],
        "universe_domain": st.secrets["firebase_credentials"]["universe_domain"]
    })
    firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

# Function to insert a project into Firestore
def insert_project_to_firestore(project_name, go_live_date):
    try:
        # Access Firestore collection "projects"
        project_ref = db.collection('projects').document(project_name)
        project_ref.set({
            'project_name': project_name,
            'go_live_date': go_live_date
        })
        st.success(f"Project '{project_name}' added successfully!")
    except Exception as e:
        st.error(f"Error inserting project: {e}")
        st.write(e)  # Debug information

# Function to load all projects from Firestore
def load_projects_from_firestore():
    try:
        # Access Firestore collection "projects"
        projects_ref = db.collection('projects')
        projects = {}
        docs = projects_ref.stream()
        for doc in docs:
            project = doc.to_dict()
            projects[doc.id] = project['go_live_date']
        return projects
    except Exception as e:
        st.error(f"Error loading projects: {e}")
        return {}

# Streamlit Interface
st.title("Project Countdown App")

# Sidebar for admin authentication
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])

# Countdown Page
if page == "Countdown":
    projects = load_projects_from_firestore()

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

# Admin Page (for admin only)
elif page == "Setup (Admin only)":
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    if password == "admin123":  # Replace with your actual admin password
        st.session_state.is_admin = True
        st.sidebar.success("Logged in as Admin")
        
        # Add project form
        project_name = st.sidebar.text_input("Project Name")
        go_live_date = st.sidebar.text_input("Go Live Date (YYYY-MM-DD HH:MM:SS)", value=str(datetime.datetime.now()))

        if st.sidebar.button("Add Project"):
            try:
                go_live_date = datetime.datetime.strptime(go_live_date, "%Y-%m-%d %H:%M:%S")
                insert_project_to_firestore(project_name, go_live_date)
            except ValueError:
                st.sidebar.error("Invalid Go Live Date format. Please use YYYY-MM-DD HH:MM:SS.")

        # Delete project form
        projects = load_projects_from_firestore()
        if projects:
            project_to_delete = st.sidebar.selectbox("Delete Project", list(projects.keys()))
            if st.sidebar.button("Delete"):
                try:
                    db.collection('projects').document(project_to_delete).delete()
                    st.sidebar.success(f"Deleted {project_to_delete}")
                except Exception as e:
                    st.sidebar.error(f"Error deleting project: {e}")
        else:
            st.sidebar.write("No projects to delete.")
    else:
        st.sidebar.write("Please log in to manage projects.")

