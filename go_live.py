import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import sqlite3
import datetime
import time
from io import BytesIO

# Firebase initialization
cred_dict = st.secrets["firebase"]
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()

ADMIN_PASSWORD = "admin123"

# SQLite Database setup
def drop_table():
    conn = sqlite3.connect('projects.db')
    conn.execute('DROP TABLE IF EXISTS projects')
    conn.commit()
    conn.close()

def create_db():
    conn = sqlite3.connect('projects.db')
    conn.execute('''
    CREATE TABLE IF NOT EXISTS projects (
        project_name TEXT,
        go_live_date TEXT
    )''')
    conn.commit()
    conn.close()

def insert_project(project_name, go_live_date):
    conn = sqlite3.connect('projects.db')
    conn.execute('INSERT INTO projects (project_name, go_live_date) VALUES (?, ?)', 
                 (project_name, go_live_date))
    conn.commit()
    conn.close()

def delete_project(project_name):
    conn = sqlite3.connect('projects.db')
    conn.execute('DELETE FROM projects WHERE project_name = ?', (project_name,))
    conn.commit()
    conn.close()

def load_projects():
    conn = sqlite3.connect('projects.db')
    cursor = conn.execute('SELECT project_name, go_live_date FROM projects')
    projects = {row[0]: datetime.datetime.strptime(row[1], '%Y-%m-%d %H:%M:%S') for row in cursor.fetchall()}
    conn.close()
    return projects

def upload_file(uploaded_file):
    df = pd.read_excel(uploaded_file)
    if 'Project Name' not in df.columns or 'Go Live Date' not in df.columns:
        st.error('Excel must have "Project Name" and "Go Live Date" columns')
        return
    
    for _, row in df.iterrows():
        project_name = row['Project Name']
        go_live_date = pd.to_datetime(row['Go Live Date']).strftime('%Y-%m-%d %H:%M:%S')
        insert_project(project_name, go_live_date)
        
        # Also upload to Firebase Firestore
        db.collection("projects").add({
            'project_name': project_name,
            'go_live_date': go_live_date
        })
    
    st.success('Projects uploaded to both SQLite and Firebase')

def generate_template():
    data = {
        'Project Name': ['Project A', 'Project B'],
        'Go Live Date': ['2024-12-01 12:00:00', '2024-12-15 15:00:00']
    }
    df = pd.DataFrame(data)
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    st.download_button(label="Download Project Template", data=buffer, file_name="project_template.xlsx")

# Streamlit UI
st.title('Project Management System')

create_db()  # Initialize DB

if st.button('Clear Projects'):
    drop_table()
    create_db()
    st.success('Database cleared')

tab1, tab2, tab3 = st.tabs(["Projects", "Upload", "Admin"])

# Tab 1: View Projects
with tab1:
    st.header('All Projects')
    projects = load_projects()
    if projects:
        for project, go_live in projects.items():
            st.write(f"{project}: {go_live}")
    else:
        st.write("No projects found.")

# Tab 2: Upload Projects
with tab2:
    st.header("Upload Projects")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx"])
    if uploaded_file:
        upload_file(uploaded_file)

# Tab 3: Admin
with tab3:
    st.header("Admin Panel")
    password = st.text_input("Enter Admin Password", type="password")
    if password == ADMIN_PASSWORD:
        st.success("Welcome, Admin!")
        if st.button('Download Project Template'):
            generate_template()
        st.text_area("Add additional administrative information here.")
    else:
        st.warning("Incorrect password.")
