import streamlit as st
import datetime
import time

# Hardcoded list of projects with their "Go Live" dates
projects = {
    "Mobile Attendance Tool (Malaysia)": datetime.datetime(2024, 12, 2, 10, 0),
    "Empty Release Order (Thailand)": datetime.datetime(2024, 11, 25, 14, 0)
}

# Streamlit app title
st.title("Go Live Countdown!")

# Dropdown menu for selecting project
selected_project = st.selectbox("Select a project", options=list(projects.keys()))

# Function to calculate time left until Go Live
def get_time_left(go_live_date):
    now = datetime.datetime.now()
    time_left = go_live_date - now
    return time_left

# Display introductory message
#st.title(f"**{selected_project}**")
st.write(f"The Go Live date for **{selected_project}** is **{projects[selected_project]:%Y-%m-%d %H:%M:%S}**.")

# Placeholder for the countdown text (for animation effect)
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
