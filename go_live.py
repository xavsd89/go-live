import streamlit as st
import pandas as pd
import sqlite3
import datetime
import time
from io import BytesIO

# Set the admin password (replace with your own secure password in a real app)
ADMIN_PASSWORD = "admin123"

# Function to drop the existing table if it exists (this should only be used once, during initial setup)
def drop_existing_table():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS projects')  # Drops the table if it exists
    conn.commit()
    conn.close()

# Function to create an SQLite database and store project details
def create_db():
    # Connect to SQLite database (it will create the database file if it doesn't exist)
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    
    # Create the table with correct columns (project_name and go_live_date)
    c.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        project_name TEXT, 
        go_live_date TEXT
    )''')
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()

# Function to insert project details into the database
def insert_project_to_db(project_name, go_live_date):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('INSERT INTO projects (project_name, go_live_date) VALUES (?, ?)', 
              (project_name, go_live_date))
    conn.commit()
    conn.close()

# Function to load project details from the database
def load_projects_from_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT project_name, go_live_date FROM projects')
    rows = c.fetchall()
    conn.close()
    return {row[0]: datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') for row in rows}

# Function to handle Excel file upload and store in the database
def handle_file_upload(uploaded_file):
    # Read the uploaded Excel file
    df = pd.read_excel(uploaded_file)
    
    # Check if the expected columns are present
    if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
        st.error('Excel file must contain "Project Name" and "Go Live Date" columns.')
        return
    
    # Insert project details into the database
    for _, row in df.iterrows():
        project_name = row['Project Name']
        go_live_date = pd.to_datetime(row['Go Live Date']).strftime('%Y-%m-%d %H:%M:%S')  # Convert to string
        insert_project_to_db(project_name, go_live_date)
    
    # Reload the projects into session state to ensure the countdown page has the latest data
    st.session_state.projects = load_projects_from_db()

    # Provide feedback to the admin
    st.success('Projects uploaded successfully!')

# Function to generate an Excel template for first-time users
def generate_excel_template():
    # Create a DataFrame with the required structure
    template_data = {
        'Project Name': ['Project A', 'Project B'],
        'Go Live Date': ['2024-12-01 12:00:00', '2024-12-15 15:00:00']
    }
    df = pd.DataFrame(template_data)
    
    # Save the DataFrame to a BytesIO object (to send as download)
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    
    return excel_buffer

# Streamlit app title
st.title("Go Live Countdown App")

# Admin login section in sidebar
def admin_login():
    password = st.sidebar.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.session_state.is_admin = True
        st.sidebar.success("You are logged in as Admin.")
    else:
        st.session_state.is_admin = False

# Drop the existing table and create a new one (if needed)
drop_existing_table()  # Drop the old table if it exists (this should be used once)
create_db()  # Create the table with the correct schema

# Check if the user is admin (session management)
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Sidebar page selection
page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])  # Updated label here

# Page for Countdown (View Countdown for selected project)
if page == "Countdown":
    # Reload the project data every time the Countdown page is accessed
    if 'projects' not in st.session_state:
        st.session_state.projects = load_projects_from_db()

    projects = st.session_state.projects

    if projects:  # Ensure that there are projects available
        selected_project = st.selectbox("Select a project", options=list(projects.keys()))

        # Function to calculate time left until Go Live
        def get_time_left(go_live_date):
            now = datetime.datetime.now()
            time_left = go_live_date - now
            return time_left

        # Display introductory message
        st.write(f"The Go Live date for **{selected_project}** is **{projects[selected_project]:%Y-%m-%d %H:%M:%S}**.")

        countdown_placeholder = st.empty()

        # Dynamically update the countdown
        time_left = get_time_left(projects[selected_project])
        while time_left > datetime.timedelta(0):
            days_left = time_left.days
            hours_left, remainder = divmod(time_left.seconds, 3600)
            minutes_left, seconds_left = divmod(remainder, 60)
            countdown_text = f"{days_left} days {hours_left} hours {minutes_left} minutes {seconds_left} seconds"
            countdown_placeholder.markdown(f"### **{countdown_text}**")
            time.sleep(1)  # Optional: to slow down refresh rate
            time_left = get_time_left(projects[selected_project])  # Recalculate time_left

        countdown_placeholder.markdown("### The Go Live event is happening NOW!")
    else:
        st.write("No projects found in the database. Please upload project details.")

# Page for Setup (Admin only) (Admin functionalities like file upload, delete project)
elif page == "Setup (Admin only)":  # Updated label here
    # Admin login in the sidebar
    admin_login()

    if st.session_state.is_admin:
        # Admin functionalities (modify, add, delete)
        st.sidebar.header("Setup: Modify Project Data")  # Updated header here

        # Provide the option to download the Excel template for first-time users
        st.sidebar.subheader("Download Excel Template")
        excel_template = generate_excel_template()
        st.sidebar.download_button(
            label="Download Project Excel Template",
            data=excel_template,
            file_name="project_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # File upload for admin
        uploaded_file = st.sidebar.file_uploader("Upload Excel File (Admin Only)", type=["xlsx"])
        if uploaded_file is not None:
            handle_file_upload(uploaded_file)

        # Allow deleting a project
        projects = st.session_state.projects
        if projects:  # If there are projects in the database
            delete_project = st.sidebar.selectbox("Select a project to delete", options=list(projects.keys()))
            if st.sidebar.button("Delete Project"):
                delete_project_from_db(delete_project)
                # After deletion, reload projects
                st.session_state.projects = load_projects_from_db()
                st.sidebar.success(f"Project '{delete_project}' has been deleted.")
        else:
            st.sidebar.write("No projects available to delete.")
    else:
        st.sidebar.write("Please log in as an Admin to modify or delete project data.")
