import streamlit as st
import pandas as pd
from io import BytesIO
import sqlite3
import datetime
import time

# Set the admin password (replace with your own secure password in a real app)
ADMIN_PASSWORD = "admin123"

# Function to drop the existing table if it exists
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

# Function to delete project from the database
def delete_project_from_db(project_name):
    conn = sqlite3.connect('projects.db')
    c = conn.cursor()
    c.execute('DELETE FROM projects WHERE project_name = ?', (project_name,))
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
    st.success('Projects uploaded successfully!')

# Function to generate the Excel template for first-time users
def generate_template():
    data = {
        'Project Name': ['Project A', 'Project B'],
        'Go Live Date': ['2024-12-01 12:00:00', '2024-12-15 15:00:00']
    }
    df = pd.DataFrame(data)
    # Creating an in-memory Excel file using BytesIO
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)  # Go back to the start of the buffer
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
page = st.sidebar.radio("Select Page", ["Countdown", "Setup (Admin only)"])

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

        # Placeholder for the countdown text
        countdown_placeholder = st.empty()

        # Countdown logic and display
        while True:
            # Get the "Go Live" date for the selected project
            go_live_date = projects[selected_project]
            time_left = get_time_left(go_live_date)

            # If the event is in the future, show the countdown
            if time_left > datetime.timedelta(0):
                # Break the time left into days, hours, minutes, and seconds
                days_left = time_left.days
                hours_left, remainder = divmod(time_left.seconds, 3600)
                minutes_left, seconds_left = divmod(remainder, 60)

                countdown_text = f"{days_left} days {hours_left} hours {minutes_left} minutes {seconds_left} seconds"
                
                # Use the placeholder to update the countdown text with animation effect
                countdown_placeholder.markdown(f"### **{countdown_text}**")
            else:
                countdown_placeholder.markdown("### The Go Live event is happening NOW!")

            # Refresh every second (1 second delay)
            time.sleep(1)

    else:
        st.write("No projects found in the database. Please upload project details.")

# Page for Setup (Admin Only)
elif page == "Setup (Admin only)":
    # Admin login in the sidebar
    admin_login()

    if st.session_state.is_admin:
        # Admin functionalities (modify, add, delete)
        st.sidebar.header("Admin: Modify Project Data")

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

        # Provide the download link for Excel template
        st.sidebar.subheader("Download Excel Template")
        template = generate_template()
        st.sidebar.download_button(
            label="Download Excel Template",
            data=template,
            file_name="project_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    else:
        st.sidebar.write("Please log in as an Admin to modify or delete project data.")
