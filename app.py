from datetime import date

import pandas as pd
import streamlit as st

import db
from validators import CATEGORIES, TYPES, validate_transaction

st.set_page_config(page_title="Transaction Management System", page_icon="💰", layout="wide")


@st.cache_resource
def setup():
    db.init_db()
    return True


def to_df(rows):
    df = pd.DataFrame(rows)
    if not df.empty:
        df["amount"] = df["amount"].astype(float)
    return df


def show_errors(errors):
    for e in errors:
        st.error(e)


# ---------------- Pages ----------------
def dashboard():
    st.header("Dashboard")
    s = db.get_summary()
    income, expense = float(s["income"]), float(s["expense"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Income", f"₹{income:,.2f}")
    c2.metric("Total Expense", f"₹{expense:,.2f}")
    c3.metric("Balance", f"₹{income - expense:,.2f}")
    c4.metric("Transactions", s["total"])

    st.subheader("Expenses by category")
    cats = to_df(db.get_category_totals())
    if cats.empty:
        st.info("No expenses recorded yet.")
    else:
        cats["total"] = cats["total"].astype(float)
        st.bar_chart(cats.set_index("category")["total"])

    st.subheader("Recent transactions")
    recent = to_df(db.get_transactions())
    if not recent.empty:
        st.dataframe(recent.head(5), use_container_width=True, hide_index=True)


def add_page():
    st.header("Add Transaction")
    with st.form("add_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        txn_date = c1.date_input("Date", value=date.today(), max_value=date.today())
        txn_type = c2.selectbox("Type", TYPES)
        description = st.text_input("Description", max_chars=255)
        c3, c4 = st.columns(2)
        category = c3.selectbox("Category", CATEGORIES)
        amount = c4.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f")
        submitted = st.form_submit_button("Save Transaction")

    if submitted:
        clean, errors = validate_transaction(txn_date, description, category, txn_type, amount)
        if errors:
            show_errors(errors)
        else:
            new_id = db.add_transaction(clean)
            st.success(f"Transaction #{new_id} saved.")


def filter_widgets(key):
    with st.expander("Search & Filters", expanded=True):
        search = st.text_input("Search description / category", key=f"{key}_s")
        c1, c2, c3 = st.columns(3)
        t = c1.selectbox("Type", ["All"] + TYPES, key=f"{key}_t")
        cat = c2.selectbox("Category", ["All"] + CATEGORIES, key=f"{key}_c")
        order = c3.selectbox("Sort by date", ["Newest first", "Oldest first"], key=f"{key}_o")
        c4, c5, c6, c7 = st.columns(4)
        use_dates = c4.checkbox("Filter by date", key=f"{key}_ud")
        d_from = c5.date_input("From", value=date(date.today().year, 1, 1), key=f"{key}_f", disabled=not use_dates)
        d_to = c6.date_input("To", value=date.today(), key=f"{key}_to", disabled=not use_dates)
        min_a = c7.number_input("Min amount", min_value=0.0, step=1.0, key=f"{key}_mn")
        max_a = st.number_input("Max amount (0 = no limit)", min_value=0.0, step=1.0, key=f"{key}_mx")

    errors = []
    if use_dates and d_from > d_to:
        errors.append("'From' date cannot be after 'To' date.")
    if max_a and min_a > max_a:
        errors.append("Min amount cannot exceed max amount.")
    if errors:
        show_errors(errors)
        return None
    return dict(search=search.strip() or None, txn_type=t, category=cat,
                date_from=d_from if use_dates else None,
                date_to=d_to if use_dates else None,
                min_amount=min_a or None, max_amount=max_a or None,
                order="ASC" if order == "Oldest first" else "DESC")


def manage_page():
    st.header("Manage Transactions")
    filters = filter_widgets("m")
    if filters is None:
        return
    rows = db.get_transactions(**filters)
    df = to_df(rows)
    st.caption(f"{len(df)} record(s) found")
    if df.empty:
        st.info("No transactions match your criteria.")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download CSV", df.to_csv(index=False), "transactions.csv", "text/csv")

    st.subheader("Edit or delete")
    labels = {r["id"]: f"#{r['id']} | {r['txn_date']} | {r['description']} | {r['txn_type']} ₹{float(r['amount']):,.2f}"
              for r in rows}
    txn_id = st.selectbox("Select a transaction", list(labels), format_func=labels.get)
    rec = db.get_transaction(txn_id)
    if not rec:
        st.warning("That transaction no longer exists.")
        return

    with st.form(f"edit_{txn_id}"):
        c1, c2 = st.columns(2)
        e_date = c1.date_input("Date", value=rec["txn_date"], max_value=date.today())
        e_type = c2.selectbox("Type", TYPES, index=TYPES.index(rec["txn_type"]))
        e_desc = st.text_input("Description", value=rec["description"], max_chars=255)
        c3, c4 = st.columns(2)
        e_cat = c3.selectbox("Category", CATEGORIES,
                             index=CATEGORIES.index(rec["category"]) if rec["category"] in CATEGORIES else 0)
        e_amt = c4.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f", value=float(rec["amount"]))
        save = st.form_submit_button("Update")
    if save:
        clean, errors = validate_transaction(e_date, e_desc, e_cat, e_type, e_amt)
        if errors:
            show_errors(errors)
        else:
            db.update_transaction(txn_id, clean)
            st.success("Transaction updated. Refresh the table by interacting with any control.")

    confirm = st.checkbox("I confirm I want to delete this transaction", key=f"cf_{txn_id}")
    if st.button("Delete", type="primary", disabled=not confirm):
        if db.delete_transaction(txn_id):
            st.success("Transaction deleted.")
            st.rerun()
        else:
            st.warning("Nothing was deleted.")


def history_page():
    st.header("Transaction History")
    filters = filter_widgets("h")
    if filters is None:
        return
    filters["order"] = "ASC"  # chronological so the running balance is correct
    df = to_df(db.get_transactions(**filters))
    if df.empty:
        st.info("No history to show.")
        return
    df["signed"] = df.apply(lambda r: r["amount"] if r["txn_type"] == "Income" else -r["amount"], axis=1)
    df["running_balance"] = df["signed"].cumsum()
    st.line_chart(df.set_index("id")["running_balance"])

    df["txn_date"] = pd.to_datetime(df["txn_date"])
    monthly = (df.assign(month=df["txn_date"].dt.to_period("M").astype(str))
                 .pivot_table(index="month", columns="txn_type", values="amount", aggfunc="sum", fill_value=0))
    st.subheader("Monthly summary")
    st.bar_chart(monthly)
    st.dataframe(df.drop(columns="signed").sort_values("txn_date", ascending=False),
                 use_container_width=True, hide_index=True)


# ---------------- Main ----------------
def main():
    st.title("💰 Transaction Management System")
    try:
        setup()
    except db.DatabaseError as e:
        st.error("Could not connect to MySQL. Check your `.env` settings and that MySQL is running.")
        st.code(str(e))
        st.stop()

    page = st.sidebar.radio("Navigate", ["Dashboard", "Add Transaction", "Manage Transactions", "History"])
    pages = {"Dashboard": dashboard, "Add Transaction": add_page,
             "Manage Transactions": manage_page, "History": history_page}
    try:
        pages[page]()
    except db.DatabaseError as e:
        st.error("A database error occurred. Your data was not changed.")
        st.code(str(e))
    except Exception as e:  # last-resort guard so the app never crashes blank
        st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
