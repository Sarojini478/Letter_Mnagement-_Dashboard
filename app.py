# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import base64

# ===== CONFIG =====
st.set_page_config(page_title="Letter Management System", layout="wide")
FILE_PATH = "letters.xlsx"

# ===== LOAD IMAGE =====
def get_base64(file):
    with open(file, "rb") as f:
        return base64.b64encode(f.read()).decode()

ship_img = get_base64("ship.png")

# ===== BACKGROUND =====
st.markdown(f"""
<style>
.stApp {{
    background: linear-gradient(to right, #e0f2fe, #eef2ff);
}}

.stApp::before {{
    content: "";
    background-image: url("data:image/png;base64,{ship_img}");
    background-size: 800px;
    background-repeat: no-repeat;
    background-position: center;
    opacity: 0.06;
    position: fixed;
    width: 100%;
    height: 100%;
}}
</style>
""", unsafe_allow_html=True)

# ===== USERS =====
USER_CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "viewer"}
}

# ===== LOGIN =====
def login():
    col1, col2, col3 = st.columns([2,2,2])

    with col2:
        st.image("hsl_logo.png", width=120)
        st.markdown("<h2 style='text-align:center;color:#0b3d91;'>Letter Management System</h2>", unsafe_allow_html=True)

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if username in USER_CREDENTIALS and USER_CREDENTIALS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = USER_CREDENTIALS[username]["role"]
            else:
                st.error("Invalid credentials")

# ===== SESSION =====
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

role = st.session_state.get("role", "viewer")

# ===== HEADER =====
st.markdown("<h1 style='text-align:center;color:#0b3d91;'>HSL Letter Management Dashboard</h1>", unsafe_allow_html=True)

# ===== LOAD DATA =====
df = pd.read_excel(FILE_PATH)

# ===== DATE SAFE =====
df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
df["Due Date"] = pd.to_datetime(df["Due Date"], errors="coerce", dayfirst=True)

# ===== AUTO STATUS =====
replied = df["Reference Letter No"].dropna().unique()

df.loc[df["Letter Type"]=="Inward","Status"] = df["Letter No"].apply(
    lambda x: "Closed" if x in replied else "Pending"
)

# ===== OVERDUE =====
today = pd.to_datetime(datetime.today())
df["Overdue"] = (df["Status"]=="Pending") & (df["Due Date"]<today)

# ===== SIDEBAR FILTERS =====
st.sidebar.title("🔍 Filters")

dept = st.sidebar.selectbox("Department", ["All"] + list(df["Department"].dropna().unique()))
person = st.sidebar.selectbox("Assigned To", ["All"] + list(df["Assigned To"].dropna().unique()))
status = st.sidebar.selectbox("Status", ["All","Pending","Closed"])

filtered_df = df.copy()

if dept != "All":
    filtered_df = filtered_df[filtered_df["Department"] == dept]

if person != "All":
    filtered_df = filtered_df[filtered_df["Assigned To"] == person]

if status != "All":
    filtered_df = filtered_df[filtered_df["Status"] == status]

# ===== KPI =====
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Letters", len(df))
c2.metric("Pending", len(df[df["Status"]=="Pending"]))
c3.metric("Closed", len(df[df["Status"]=="Closed"]))
c4.metric("Overdue", df["Overdue"].sum())

st.markdown("---")

# ===== TABS =====
if role == "admin":
    tab1, tab2 = st.tabs(["📊 Dashboard", "✏️ Manage"])
else:
    tab1 = st.tabs(["📊 Dashboard"])[0]

# ===== DASHBOARD =====
with tab1:

    st.subheader("📌 Pending Letters")

    st.dataframe(
        filtered_df[filtered_df["Status"]=="Pending"]
        [["Letter No","Department","Assigned To","Due Date","Remarks"]],
        use_container_width=True
    )

    col1, col2 = st.columns(2)

    with col1:
        total_df = df.groupby("Department").size().reset_index(name="Total")
        pending_df = df[df["Status"]=="Pending"].groupby("Department").size().reset_index(name="Pending")

        merged = pd.merge(total_df, pending_df, on="Department", how="left").fillna(0)

        fig = px.bar(merged, x="Department", y=["Total","Pending"], barmode="group",
                     title="Department-wise Letters")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        person_df = df[df["Status"]=="Pending"].groupby("Assigned To").size().reset_index(name="Pending")

        fig2 = px.bar(person_df, x="Assigned To", y="Pending",
                      title="Pending Letters per Person")
        st.plotly_chart(fig2, use_container_width=True)

# ===== ADMIN =====
if role == "admin":
    with tab2:
        st.subheader("➕ Add Letter")

        with st.form("form"):
            lno = st.text_input("Letter No")
            date = st.date_input("Date")
            due = st.date_input("Due Date")

            if due < date:
                st.error("Due date cannot be earlier than Date")

            dept = st.text_input("Department")
            person = st.text_input("Assigned To")
            status = st.selectbox("Status", ["Pending","Closed"])
            ltype = st.selectbox("Letter Type", ["Inward","Outward"])

            if ltype == "Outward":
                ref = st.selectbox("Reference", [""] + list(df["Letter No"]))
            else:
                ref = ""

            remarks = st.text_area("Remarks")

            submit = st.form_submit_button("Add Letter")

            if submit:
                if due < date:
                    st.error("Fix date issue")
                else:
                    new = pd.DataFrame([[lno,date,dept,person,status,due,ltype,ref,remarks]],
                    columns=["Letter No","Date","Department","Assigned To","Status","Due Date","Letter Type","Reference Letter No","Remarks"])

                    df = pd.concat([df,new],ignore_index=True)
                    df.to_excel(FILE_PATH,index=False)

                    st.success("Added successfully")

# ===== LOGOUT =====
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()