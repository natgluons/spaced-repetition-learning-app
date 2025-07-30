import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- DB Setup ---
conn = sqlite3.connect('learning.db', check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        question TEXT,
        answer TEXT,
        last_reviewed DATE,
        next_review DATE,
        interval_days INTEGER
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY,
        question_id INTEGER,
        review_date DATE
    )
''')

conn.commit()

# --- Functions ---
def add_question(question, answer):
    today = datetime.today().date()
    c.execute('INSERT INTO questions (question, answer, last_reviewed, next_review, interval_days) VALUES (?, ?, ?, ?, ?)',
              (question, answer, None, today, 3))
    conn.commit()

def get_all_questions():
    c.execute('SELECT * FROM questions')
    return c.fetchall()

def get_grouped_questions():
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)

    c.execute('SELECT * FROM questions WHERE next_review <= ?', (today,))
    due_today = c.fetchall()

    c.execute('SELECT * FROM questions WHERE next_review = ?', (tomorrow,))
    due_tomorrow = c.fetchall()

    c.execute('SELECT * FROM questions WHERE next_review > ?', (tomorrow,))
    future = c.fetchall()

    return due_today, due_tomorrow, future

def update_review(id, remembered=True):
    today = datetime.today().date()
    c.execute('SELECT interval_days FROM questions WHERE id=?', (id,))
    interval = c.fetchone()[0]
    
    if remembered:
        new_interval = min(interval * 2, 60)
    else:
        new_interval = 3
    
    next_review = today + timedelta(days=new_interval)
    c.execute('UPDATE questions SET last_reviewed=?, next_review=?, interval_days=? WHERE id=?',
              (today, next_review, new_interval, id))
    
    # Log review
    c.execute('INSERT INTO reviews (question_id, review_date) VALUES (?, ?)', (id, today))
    conn.commit()

def get_reviews_per_day():
    c.execute('SELECT review_date, COUNT(*) FROM reviews GROUP BY review_date')
    data = c.fetchall()
    if not data:
        return pd.DataFrame(columns=['date', 'count'])
    
    df = pd.DataFrame(data, columns=['date', 'count'])
    df['date'] = pd.to_datetime(df['date'])
    
    # Fill missing days
    date_range = pd.date_range(df['date'].min(), datetime.today())
    df_full = pd.DataFrame(date_range, columns=['date']).merge(df, on='date', how='left').fillna(0)
    return df_full

def get_questions_reviewed_on(date):
    c.execute('''
        SELECT q.question 
        FROM reviews r
        JOIN questions q ON r.question_id = q.id
        WHERE r.review_date = ?
    ''', (date,))
    return [row[0] for row in c.fetchall()]

# --- Streamlit App ---
st.title("Spaced Repetition Learning App")
st.caption(f"Today's Date: {datetime.today().strftime('%A, %d %B %Y')}")

tab1, tab2, tab3, tab4 = st.tabs(["🔁 Review", "📊 Dashboard", "📖 All Questions", "➕ Add Question"])

# --- Tab 1: Review ---
with tab1:
    due_today, due_tomorrow, future = get_grouped_questions()

    st.subheader(f"To Review Today: {len(due_today)} question{'s' if len(due_today) != 1 else ''}")

    # If reviewing a question
    if "reviewing" in st.session_state:
        row = st.session_state["reviewing"]
        st.markdown("---")
        st.markdown(f"<span style='font-size: 16px;'><b>Question:</b> {row[1]}</span>", unsafe_allow_html=True)
        user_answer = st.text_area("Your Answer (you can write code here)")

        # Initialize answer toggle
        if "show_answer" not in st.session_state:
            st.session_state["show_answer"] = False

        # Reveal/Close Answer
        col1, col2 = st.columns([1, 2])
        with col1:
            if not st.session_state["show_answer"]:
                if st.button("Reveal Answer", key="reveal"):
                    st.session_state["show_answer"] = True
                    st.rerun()
            else:
                if st.button("Close Answer", key="close"):
                    st.session_state["show_answer"] = False
                    st.rerun()

        # Display answer if toggled
        if st.session_state["show_answer"]:
            st.info(f"Correct Answer:\n\n{row[2]}")

        # Mark as reviewed
        if st.button("✅ Mark as reviewed", key="mark_reviewed"):
            update_review(row[0], True)
            del st.session_state["reviewing"]
            st.session_state["show_answer"] = False
            st.success("Marked as reviewed!")
            st.rerun()

    # If no active review
    elif not due_today:
        st.info("Nothing due today!")
    else:
        for row in due_today:
            if st.button("Review Now", key=f"today_{row[0]}"):
                st.session_state["reviewing"] = row
                st.rerun()

    st.subheader(f"To Review Tomorrow: {len(due_tomorrow)} question{'s' if len(due_tomorrow) != 1 else ''}")
    if not due_tomorrow:
        st.info("No reviews scheduled for tomorrow")
    else:
        for row in due_tomorrow:
            st.write(f"- {row[1]}")

# --- Tab 2: Dashboard ---
with tab2:
    # Metrics
    today = datetime.today().date()

    c.execute('SELECT COUNT(*) FROM questions')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM questions WHERE next_review = ?', (today,))
    due_today = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM reviews WHERE review_date = ?', (today,))
    reviewed_today = c.fetchone()[0]
    c.execute('SELECT COUNT(DISTINCT question_id) FROM reviews')
    reviewed_total = c.fetchone()[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Questions", total)
    col2.metric("Due Today", due_today)
    col3.metric("Reviewed Today", reviewed_today)
    col4.metric("Total Reviewed", reviewed_total)

    df_full = get_reviews_per_day()
    if not df_full.empty:
        # --- Default range ---
        start_date = datetime(2025, 7, 30)
        end_date = start_date + timedelta(days=30)
        all_dates = pd.date_range(start=start_date, end=end_date)

        counts = dict(zip(df_full['date'], df_full['count']))

        weeks = [(d - start_date).days // 7 for d in all_dates]
        # Map weekday to Sun=0 ... Sat=6
        weekdays = [(d.weekday() + 1) % 7 for d in all_dates]
        values = [counts.get(d, None) for d in all_dates]  # None for no data = transparent

        fig = go.Figure(data=go.Heatmap(
            x=weeks,
            y=weekdays,
            z=values,
            text=[f"{d.date()}: {counts.get(d, 0)} reviews" for d in all_dates],
            hoverinfo="text",
            colorscale=[
                [0, "#ebedf0"],
                [0.2, "#c6e48b"],
                [0.4, "#7bc96f"],
                [0.6, "#239a3b"],
                [1.0, "#196127"]
            ],
            zmin=0,
            zmax=max(counts.values()) if counts else 1,
            showscale=False,
            hoverongaps=False
        ))

        fig.update_layout(
            title="📅 Review Activity",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True),
            yaxis=dict(
                showgrid=False,
                zeroline=False,
                tickmode="array",
                tickvals=[0, 1, 2, 3, 4, 5, 6],
                ticktext=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
                fixedrange=True,
                autorange='reversed'  # 🔥 Flip vertical order
            ),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            dragmode=False,
            height=180,
            margin=dict(l=20, r=20, t=30, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        selected_date = st.date_input("📌 Select a date to see reviewed questions", today)
        reviewed_questions = get_questions_reviewed_on(selected_date)
        if reviewed_questions:
            st.success(f"Reviewed on {selected_date}:")
            for q in reviewed_questions:
                st.write(f"- {q}")
        else:
            st.info("No questions reviewed on this date")
    else:
        st.info("No review data available yet")

# --- Tab 3: All Questions ---
with tab3:
    # Reset all button
    if st.button("🔄 Reset All Review Dates"):
        today = datetime.today().date()
        c.execute('UPDATE questions SET last_reviewed = NULL, next_review = ?, interval_days = 3', (today,))
        conn.commit()
        if "reviewing" in st.session_state:
            del st.session_state["reviewing"]
        st.success("All questions have been reset!")
        st.rerun()

    all_qs = get_all_questions()
    if not all_qs:
        st.info("No questions added yet!")
    else:
        for row in all_qs:
            with st.expander(f"{row[1]} (Next Review: {row[4]})"):
                if st.button("Add to today's review", key=f"all_{row[0]}"):
                    st.success("Added to today's review. Open tab \"Review\" to start reviewing.")

# --- Tab 4: Add Question ---
with tab4:
    q = st.text_area("Enter Question")
    a = st.text_area("Enter Answer")
    if st.button("Add"):
        if q and a:
            add_question(q, a)
            st.success("Question added!")
        else:
            st.warning("Please fill both question and answer.")
