import streamlit as st
import pandas as pd
import datetime
import psycopg2
from sqlalchemy import create_engine
import urllib

# Initialize the app
st.set_page_config(page_title="Expense & Income Tracker", layout="centered")
st.title("Expense & Income Tracker")

# Database connection - Ensure password special characters are URL encoded
password = "111Dotstudio100#@"
encoded_password = urllib.parse.quote_plus(password)
DATABASE_URL = f"postgresql://postgres:{encoded_password}@localhost:5432/tracker_db"

engine = create_engine(DATABASE_URL)

# Initialize database
def init_db():
    with engine.connect() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS expenses (
                        id SERIAL PRIMARY KEY,
                        date DATE,
                        category TEXT,
                        description TEXT,
                        amount NUMERIC
                    )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS income (
                        id SERIAL PRIMARY KEY,
                        date DATE,
                        source TEXT,
                        description TEXT,
                        amount NUMERIC
                    )''')

init_db()

# Function to add an expense
def add_expense_to_db(date, category, description, amount):
    with engine.connect() as conn:
        conn.execute("INSERT INTO expenses (date, category, description, amount) VALUES (%s, %s, %s, %s)",
                     (date, category, description, amount))

# Function to add income
def add_income_to_db(date, source, description, amount):
    with engine.connect() as conn:
        conn.execute("INSERT INTO income (date, source, description, amount) VALUES (%s, %s, %s, %s)",
                     (date, source, description, amount))

# Function to fetch expenses
def fetch_expenses():
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM expenses", conn)

# Function to fetch income
def fetch_income():
    with engine.connect() as conn:
        return pd.read_sql("SELECT * FROM income", conn)

# Tabs for functionality
tabs = st.tabs(["Add Expense", "Add Income", "View Transactions", "Analytics"])

with tabs[0]:
    st.header("Add a New Expense")

    # Input fields for a new expense
    expense_option = st.radio("Expense Type", ["Single Expense", "Weekly Expense"], key="expense_option")

    if expense_option == "Single Expense":
        expense_date = st.date_input("Date", value=datetime.date.today(), key="expense_date")
        expense_category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"], key="expense_category")
        expense_description = st.text_input("Description", "", key="expense_description")
        expense_amount = st.number_input("Amount", min_value=0.0, step=0.01, key="expense_amount")

        if st.button("Add Expense"):
            if expense_description and expense_amount > 0:
                add_expense_to_db(expense_date, expense_category, expense_description, expense_amount)
                st.success("Expense added successfully!")
            else:
                st.error("Please fill out all fields.")
    
    elif expense_option == "Weekly Expense":
        start_date = st.date_input("Start Date", value=datetime.date.today(), key="start_date")
        include_weekends = st.checkbox("Include Saturday and Sunday?", value=True)
        weekly_amount = st.number_input("Weekly Amount", min_value=0.0, step=0.01, key="weekly_amount")
        expense_category = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Other"], key="weekly_category")
        expense_description = st.text_input("Description", "", key="weekly_description")

        if st.button("Add Weekly Expense"):
            if expense_description and weekly_amount > 0:
                daily_amount = weekly_amount / (7 if include_weekends else 5)  # Distribute based on included days

                for day_offset in range(7):  # Loop through all 7 days
                    day_date = start_date + datetime.timedelta(days=day_offset)
                    
                    # Skip Saturday (5) and Sunday (6) if weekends are excluded
                    if not include_weekends and day_date.weekday() in [5, 6]:
                        continue
                    
                    add_expense_to_db(day_date, expense_category, expense_description, daily_amount)
                
                # Display success message
                if include_weekends:
                    st.success(f"Weekly expense from {start_date} added successfully!")
                else:
                    st.success(f"Weekly expense from {start_date} (excluding weekends) added successfully!")
            else:
                st.error("Please fill out all fields.")

with tabs[1]:
    st.header("Add a New Income")

    # Input fields for new income
    income_date = st.date_input("Date", value=datetime.date.today(), key="income_date")
    income_source = st.selectbox("Source", ["Salary", "Business", "Investments", "Freelance", "Other"], key="income_source")
    income_description = st.text_input("Description", "", key="income_description")
    income_amount = st.number_input("Amount", min_value=0.0, step=0.01, key="income_amount")

    if st.button("Add Income"):
        if income_description and income_amount > 0:
            add_income_to_db(income_date, income_source, income_description, income_amount)
            st.success("Income added successfully!")
        else:
            st.error("Please fill out all fields.")

with tabs[2]:
    st.header("View Transactions")

    transaction_type = st.radio("Select transaction type:", ["Expenses", "Income"])

    if transaction_type == "Expenses":
        expense_data = fetch_expenses()
        if expense_data.empty:
            st.info("No expenses added yet.")
        else:
            st.subheader("Expenses")
            st.dataframe(expense_data, use_container_width=True)

            # Download option for expenses
            csv = expense_data.to_csv(index=False)
            st.download_button("Download Expenses as CSV", data=csv, file_name="expenses.csv", mime="text/csv")
    else:
        income_data = fetch_income()
        if income_data.empty:
            st.info("No income added yet.")
        else:
            st.subheader("Income")
            st.dataframe(income_data, use_container_width=True)

            # Download option for income
            csv = income_data.to_csv(index=False)
            st.download_button("Download Income as CSV", data=csv, file_name="income.csv", mime="text/csv")

with tabs[3]:
    st.header("Analytics")

    expense_data = fetch_expenses()
    income_data = fetch_income()

    if expense_data.empty and income_data.empty:
        st.info("No data available for analytics.")
    else:
        total_expense = expense_data["amount"].sum() if not expense_data.empty else 0
        total_income = income_data["amount"].sum() if not income_data.empty else 0
        balance = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"₹ {total_income:.2f}")
        col2.metric("Total Expense", f"₹ {total_expense:.2f}")
        col3.metric("Balance", f"₹ {balance:.2f}")

        if not expense_data.empty:
            # Expenses by category
            category_summary = expense_data.groupby("category")["amount"].sum().reset_index()
            st.subheader("Expenses by Category")
            st.bar_chart(category_summary.set_index("category"))

            # Expenses over time
            expense_data["date"] = pd.to_datetime(expense_data["date"])
            expense_date_summary = expense_data.groupby("date")["amount"].sum().reset_index()
            st.subheader("Expenses Over Time")
            st.line_chart(expense_date_summary.set_index("date"))

        if not income_data.empty:
            # Income by source
            source_summary = income_data.groupby("source")["amount"].sum().reset_index()
            st.subheader("Income by Source")
            st.bar_chart(source_summary.set_index("source"))

            # Income over time
            income_data["date"] = pd.to_datetime(income_data["date"])
            income_date_summary = income_data.groupby("date")["amount"].sum().reset_index()
            st.subheader("Income Over Time")
            st.line_chart(income_date_summary.set_index("date"))
