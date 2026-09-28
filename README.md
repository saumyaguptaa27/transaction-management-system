# Transaction Management System

Python + Streamlit + MySQL app for recording and tracking financial transactions.

## Features
- CRUD: add, view, edit, delete transactions
- Search (description/category) and filters (type, category, date range, amount range)
- Transaction history with running balance and monthly income/expense chart
- Dashboard with totals and expense breakdown; CSV export
- Input validation (amount > 0, no future dates, required fields) and error handling for DB failures
- Parameterised SQL queries (protects against SQL injection)

## Setup
1. Install Python 3.9+ and MySQL 8+, and make sure MySQL is running.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your MySQL credentials.
4. `streamlit run app.py`

The database and table are created automatically on first run
(or run `schema.sql` manually in MySQL).

## Structure
- `app.py` – Streamlit UI
- `db.py` – MySQL connection and SQL queries
- `validators.py` – input validation
- `schema.sql` – table definition
