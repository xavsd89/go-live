import streamlit as st
import pandas as pd
import sqlite3
import datetime
import time
from io import BytesIO

# Admin password setup
admin_pw = "admin123"

# Drop existing table if needed
def drop_table():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('DROP TABLE IF EXISTS projects')  # Drop table if it exists
    conn.commit()
    conn.close()

# Create database and table
def create_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS projects (
                    project_name TEXT, 
                    go_live_date TEXT)''')
    conn.commit()
    conn.close()

# Insert project into database
def add_project_to_db(name, date):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('INSERT INTO projects (project_name, go_live_date) VALUES (?, ?)', (name, date))
    conn.commit()
    conn.close()

# Load all projects from the database
def get_projects_from_db():
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('SELECT project_name, go_live_date FROM projects')
    rows = c.fetchall()
    conn.close()
    return {row[0]: datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') for row in rows}

# Handle uploaded Excel file
def handle_uploaded_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    
    # Check if required columns are in the file
    if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
        st.error('Excel file must contain "Project Name" and "Go Live Date" columns.')
        return
    
    # Insert each project into the database
    for _, row in df.iterrows():
        project_name = row['Project Name']
        go_live_date = pd.to_datetime(row['Go Live Date']).strftime('%Y-%m-%d %H:%M:%S')
        add_project_to_db(project_name, go_live_date)
    
    st.session_state.projects = get_projects_from_db()
    st.success('Projects uploaded successfully!')

# Generate an Excel template file for first-time users
def generate_template():
    data = {
        'Project Name': ['Project A', 'Project B'],
        'Go Live Date': ['2024-12-01 12:00:00', '2024-12-15 15:00:00']
    }
    df = pd.DataFrame(data)
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return excel_buffer

# Streamlit app title
st.title("Go Live Countdown App")

# Admin login
def admin_login():
    pw = st.sidebar.text_input("Enter Admin Password", type="password")
    if pw == admin_pw:
        st.session_state.is_admin = True
        st.sidebar.success("Admin logged in.")
    else:
        st.session_state.is_admin = False

# Drop table and create it
drop_table()  # Drop the table once
create_db()

# Check if user is logged in as admin
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

# Sidebar page selection
page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])

# Countdown page (view project countdown)
if page == "Countdown":
    if 'projects' not in st.session_state:
        st.session_state.projects = get_projects_from_db()

    projects = st.session_state.projects

    if projects:
        selected_project = st.selectbox("Select a project", options=list(projects.keys()))

        # Countdown timer logic
        def get_time_left(go_live_date):
            now = datetime.datetime.now()
            time_left = go_live_date - now
            return time_left

        st.write(f"The Go Live date for **{selected_project}** is **{projects[selected_project]:%Y-%m-%d %H:%M:%S}**.")

        countdown_placeholder = st.empty()

        # Update countdown every second
        time_left = get_time_left(projects[selected_project])
        while time_left > datetime.timedelta(0):
            days_left = time_left.days
            hours_left, remainder = divmod(time_left.seconds, 3600)
            minutes_left, seconds_left = divmod(remainder, 60)
            countdown_text = f"{days_left} days {hours_left} hours {minutes_left} minutes {seconds_left} seconds"
            countdown_placeholder.markdown(f"### **{countdown_text}**")
            time.sleep(1)
            time_left = get_time_left(projects[selected_project])

        countdown_placeholder.markdown("### The Go Live event is happening NOW!")
    else:
        st.write("No projects found. Please upload some project details.")

# Setup (Admin only) page for admins to upload projects and download the template
elif page == "Setup (Admin only)":
    admin_login()

    if st.session_state.is_admin:
        st.sidebar.header("Admin - Setup: Modify Project Data")

        # Excel template download link
        st.sidebar.subheader("Download Excel Template")
        template = generate_template()
        st.sidebar.download_button(
            label="Download Excel Template",
            data=template,
            file_name="project_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Admin upload file section
        uploaded_file = st.sidebar.file_uploader("Upload Project Excel (Admin only)", type=["xlsx"])
        if uploaded_file is not None:
            handle_uploaded_file(uploaded_file)

        # Allow deletion of projects
        projects = st.session_state.projects
        if projects:
            project_to_delete = st.sidebar.selectbox("Select project to delete", options=list(projects.keys()))
            if st.sidebar.button("Delete Project"):
                conn = sqlite3.connect('projects.db')
                c = conn.cursor()
                c.execute('DELETE FROM projects WHERE project_name = ?', (project_to_delete,))
                conn.commit()
                conn.close()

                st.session_state.projects = get_projects_from_db()
                st.sidebar.success(f"Project '{project_to_delete}' deleted.")
        else:
            st.sidebar.write("No projects to delete.")
    else:
        st.sidebar.write("Please log in as an Admin to manage project data.")
