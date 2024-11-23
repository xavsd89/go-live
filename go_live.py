import streamlit as st
import pandas as pd
import sqlite3
import datetime
import time
from io import BytesIO

ADMIN_PASSWORD = "admin123"

# Drop the existing projects table
def drop_table():
    conn = sqlite3.connect('projects.db')
    conn.execute('DROP TABLE IF EXISTS projects')
    conn.commit()
    conn.close()

# Create the table for storing project details
def create_db():
    conn = sqlite3.connect('projects.db')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        project_name TEXT,
        go_live_date TEXT
    )''')
    conn.commit()
    conn.close()

# Insert project into the database
def insert_project(project_name, go_live_date):
    conn = sqlite3.connect('projects.db')
    conn.execute('INSERT INTO projects (project_name, go_live_date) VALUES (?, ?)', 
                 (project_name, go_live_date))
    conn.commit()
    conn.close()

# Delete project from the database
def delete_project(project_name):
    conn = sqlite3.connect('projects.db')
    conn.execute('DELETE FROM projects WHERE project_name = ?', (project_name,))
    conn.commit()
    conn.close()

# Load all projects from the database
def load_projects():
    conn = sqlite3.connect('projects.db')
    cursor = conn.execute('SELECT project_name, go_live_date FROM projects')
    projects = {row[0]: datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') for row in cursor.fetchall()}
    conn.close()
    return projects

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

# Initialize DB if it doesn't exist
drop_table()
create_db()

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
                countdown_text = f"{days_left}d {hours_left}h {minutes_left}m {seconds_left}s"
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
