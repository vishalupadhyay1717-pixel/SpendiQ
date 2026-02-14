import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date
import numpy as np

st.set_page_config("SpendiQ Pro", page_icon="💸", layout="wide")

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None

# ---------------- DB ----------------
conn = sqlite3.connect("spendiq.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS users(username TEXT,password TEXT)")
cur.execute(
    "CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT,amount REAL,category TEXT,payment TEXT,date TEXT)"
)
cur.execute("CREATE TABLE IF NOT EXISTS budget(username TEXT,amount REAL)")
conn.commit()

# ---------------- LOGIN / REGISTER ----------------
if not st.session_state.user:

    st.title("💸 SpendiQ Pro")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")

        if st.button("Login"):
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
            if cur.fetchone():
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid login")

    with tab2:
        ru = st.text_input("New Username")
        rp = st.text_input("New Password", type="password")

        if st.button("Register"):
            cur.execute("INSERT INTO users VALUES(?,?)", (ru, rp))
            conn.commit()
            st.success("Registered! Login now.")

    st.stop()

user = st.session_state.user

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("➕ Add Expense")

    amt = st.number_input("Amount", 1.0)
    cat = st.selectbox(
        "Category", ["Food", "Travel", "Shopping", "Bills", "Fun", "Other"]
    )
    pay = st.selectbox("Payment", ["Cash", "UPI", "Card"])
    d = st.date_input("Date", value=date.today())

    if st.button("Add"):
        cur.execute(
            "INSERT INTO expenses VALUES(NULL,?,?,?,?,?)", (user, amt, cat, pay, str(d))
        )
        conn.commit()
        st.success("Added")

    st.divider()

    st.header("💰 Budget")
    b = st.number_input("Monthly Budget", 1.0)

    if st.button("Save Budget"):
        cur.execute("DELETE FROM budget WHERE username=?", (user,))
        cur.execute("INSERT INTO budget VALUES(?,?)", (user, b))
        conn.commit()

    if st.button("Logout"):
        st.session_state.user = None
        st.rerun()

# ---------------- LOAD DATA ----------------
df = pd.read_sql("SELECT * FROM expenses WHERE username=?", conn, params=(user,))

if df.empty:
    st.info("Add expenses first")
    st.stop()

df["date"] = pd.to_datetime(df["date"])

# ---------------- KPI ----------------
total = df["amount"].sum()
top = df.groupby("category")["amount"].sum().idxmax()

bd = pd.read_sql("SELECT amount FROM budget WHERE username=?", conn, params=(user,))
limit = bd["amount"][0] if not bd.empty else None

c1, c2, c3 = st.columns(3)
c1.metric("Total Spend", f"₹{int(total)}")
c2.metric("Top Category", top)
c3.metric("Entries", len(df))

if limit:
    st.progress(min(total / limit, 1.0))
    st.caption(f"{int((total/limit)*100)}% Budget Used")

# ---------------- FILTER ----------------
choice = st.selectbox("Filter Category", ["All"] + list(df["category"].unique()))
if choice != "All":
    df = df[df["category"] == choice]

# ---------------- CHARTS ----------------
cat_df = df.groupby("category")["amount"].sum().reset_index()
daily = df.groupby("date")["amount"].sum().reset_index()

l, r = st.columns(2)
l.plotly_chart(px.bar(cat_df, x="category", y="amount"), use_container_width=True)
r.plotly_chart(px.line(daily, x="date", y="amount"), use_container_width=True)

# ---------------- SMART AI ----------------
st.subheader("🤖 Smart Spending Prediction")

recent = daily["amount"].tail(7)
pred = min(recent.mean(), daily["amount"].max())
st.success(f"Tomorrow Estimated Spend: ₹{int(pred)}")

# ---------------- INSIGHTS ----------------
big = cat_df.sort_values("amount", ascending=False).iloc[0]
st.info(f"Highest spending: {big['category']} ₹{int(big['amount'])}")

if big["amount"] > total * 0.5:
    st.warning("More than 50% spending in one category!")

# ---------------- TABLE ----------------
st.dataframe(df, use_container_width=True)

# ---------------- EXPORT ----------------
st.download_button("Download CSV", df.to_csv(index=False), "expenses.csv")

# ---------------- DELETE ----------------
did = st.number_input("Delete ID", step=1)
if st.button("Delete"):
    cur.execute("DELETE FROM expenses WHERE id=?", (did,))
    conn.commit()
    st.success("Deleted")

st.caption("SpendiQ Pro • Built by Vishal")
