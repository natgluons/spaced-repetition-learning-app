import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# --- DB Setup ---
if os.environ.get("LOCAL", "0") == "1":
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
else:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Functions ---
def add_question(question, answer):
    today = datetime.today().date()
    supabase.table("questions").insert({
        "question": question,
        "answer": answer,
        "last_reviewed": None,
        "next_review": today.isoformat(),
        "interval_days": 3
    }).execute()

def get_all_questions():
    response = supabase.table("questions").select("*").execute()
    return response.data if response.data else []

def get_grouped_questions():
    today = datetime.today().date()
    tomorrow = today + timedelta(days=1)

    # Due today
    due_today = supabase.table("questions") \
        .select("*") \
        .lte("next_review", today.isoformat()) \
        .execute().data

    # Due tomorrow
    due_tomorrow = supabase.table("questions") \
        .select("*") \
        .eq("next_review", tomorrow.isoformat()) \
        .execute().data

    # Future
    future = supabase.table("questions") \
        .select("*") \
        .gt("next_review", tomorrow.isoformat()) \
        .execute().data

    return due_today, due_tomorrow, future

def get_review_history(question_id):
    response = supabase.table("reviews") \
        .select("review_date") \
        .eq("question_id", question_id) \
        .order("review_date") \
        .execute()
    return [row["review_date"] for row in response.data] if response.data else []

def update_review(question_id, reviewed=True):
    today = datetime.today().date()

    # Get current interval
    question = supabase.table("questions").select("interval_days").eq("id", question_id).execute()
    if not question.data:
        return

    interval = question.data[0]["interval_days"]
    new_interval = min(interval * 2, 60) if reviewed else 3
    next_review = today + timedelta(days=new_interval)

    # Update question
    supabase.table("questions").update({
        "last_reviewed": today.isoformat(),
        "next_review": next_review.isoformat(),
        "interval_days": new_interval
    }).eq("id", question_id).execute()

    # Insert into reviews
    supabase.table("reviews").insert({
        "question_id": question_id,
        "review_date": today.isoformat()
    }).execute()

def get_reviews_per_day():
    response = supabase.table("reviews") \
        .select("review_date") \
        .execute()

    if not response.data:
        return pd.DataFrame(columns=['date', 'count'])

    df = pd.DataFrame(response.data)

    # Ensure proper datetime conversion
    df['review_date'] = pd.to_datetime(df['review_date'])

    # Count reviews per day
    daily_counts = df.groupby(df['review_date'].dt.date).size().reset_index(name='count')

    # Convert to datetime for merging
    daily_counts['review_date'] = pd.to_datetime(daily_counts['review_date'])

    # Fill missing days
    date_range = pd.date_range(daily_counts['review_date'].min(), datetime.today())
    df_full = pd.DataFrame(date_range, columns=['date']).merge(
        daily_counts.rename(columns={'review_date': 'date'}),
        on='date',
        how='left'
    ).fillna(0)

    return df_full

def get_questions_reviewed_on(date):
    response = supabase.table("reviews") \
        .select("question_id, review_date, questions!inner(question)") \
        .eq("review_date", date.isoformat()) \
        .execute()

    if not response.data:
        return []

    return [row["questions"]["question"] for row in response.data]

#############################
# --- Streamlit App ---
st.title("Spaced Repetition Learning App")
server_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
st.caption(f"\nServer time: {server_time}")

tab1, tab2, tab3, tab4 = st.tabs(["🔁 Review", "📊 Dashboard", "📖 All Questions", "➕ Add Question"])

# --- Tab 1: Review ---
with tab1:
    due_today, _, _ = get_grouped_questions()

    st.subheader(f"To Review Today: {len(due_today)} question{'s' if len(due_today) != 1 else ''}")

    # If reviewing a question
    if "reviewing" in st.session_state:
        row = st.session_state["reviewing"]

        st.markdown("---")
        st.markdown(
            f"<span style='font-size: 16px;'><b>Question:</b> {row['question']}</span>", 
            unsafe_allow_html=True
        )
        user_answer = st.text_area("Your Answer", placeholder="(you can write code here)")

        # Initialize answer toggle
        if "show_answer" not in st.session_state:
            st.session_state["show_answer"] = False

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

        if st.session_state["show_answer"]:
            st.text_area("Correct Answer", row['answer'], height=150, disabled=True)

        if st.button("✅ Mark as reviewed", key="mark_reviewed"):
            update_review(row['id'], True)
            del st.session_state["reviewing"]
            st.session_state["show_answer"] = False
            st.success("Marked as reviewed!")
            st.rerun()
        
        # Add "See other questions" as a back button
        if st.button("<- See other questions", key="back_to_list"):
            del st.session_state["reviewing"]
            st.session_state["show_answer"] = False
            st.rerun()

        # Show review history
        review_dates = get_review_history(row['id'])
        st.markdown("---")
        st.markdown(f"**Reviewed:** {len(review_dates)} time{'s' if len(review_dates) != 1 else ''}")
        if review_dates:
            st.markdown("**Review Dates:**")
            for d in review_dates:
                st.markdown(f"- {d}")

    # If no active review
    elif not due_today:
        st.info("Nothing due today!")
    else:
        for row in due_today:
            question_text = row["question"]
            if "[" in question_text and "]" in question_text:
                question_label = f"[{question_text.split(']')[0].strip('[')}] - Review Now"
            else:
                question_label = f"{question_text} - Review Now"

            if st.button(question_label, key=f"today_{row['id']}"):
                st.session_state["reviewing"] = row
                st.rerun()

# --- Tab 2: Dashboard ---
with tab2:
    today = datetime.today().date()

    # Total questions
    total_resp = supabase.table("questions").select("id", count="exact").execute()
    total = total_resp.count if total_resp.count else 0

    # Due today
    due_today_resp = supabase.table("questions").select("id", count="exact") \
        .eq("next_review", today.isoformat()).execute()
    due_today = due_today_resp.count if due_today_resp.count else 0

    # Reviewed today
    reviewed_today_resp = supabase.table("reviews").select("id", count="exact") \
        .eq("review_date", today.isoformat()).execute()
    reviewed_today = reviewed_today_resp.count if reviewed_today_resp.count else 0

    # Total reviewed (distinct questions)
    response = supabase.table("reviews") \
        .select("question_id", count="exact") \
        .execute()

    # Count distinct question_id
    reviewed_total = len({row["question_id"] for row in response.data})

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
                autorange='reversed'  # Flip vertical order
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
        supabase.table("questions").update({
            "last_reviewed": None,
            "next_review": today.isoformat(),
            "interval_days": 3
        }).neq("id", 0).execute()  # `neq` used to target all rows
        if "reviewing" in st.session_state:
            del st.session_state["reviewing"]
        st.success("All questions have been reset!")
        st.rerun()

    # Show message only once
    if "success_msg" in st.session_state:
        st.success(st.session_state["success_msg"])
        del st.session_state["success_msg"]

    all_qs = get_all_questions()
    if not all_qs:
        st.info("No questions added yet!")
    else:
        for row in all_qs:
            with st.expander(f"{row['question']} (Next Review: {row['next_review']})"):
                col1, col2, col3 = st.columns([2, 2, 2])
                
                # --- Add to today's review ---
                with col1:
                    if st.button("Add to today's review", key=f"all_{row['id']}"):
                        today = datetime.today().date()
                        supabase.table("questions").update({
                            "next_review": today.isoformat()
                        }).eq("id", row['id']).execute()
                        st.session_state["success_msg"] = (
                            f"Added '{row['question']}' to today's review.\n\n"
                            "Check \"Review\" tab to start reviewing the added question"
                        )
                        st.rerun()

                if "success_msg" in st.session_state:
                    st.success(st.session_state["success_msg"])

                # --- Edit question ---
                with col2:
                    if st.button("✏️ Edit question", key=f"edit_{row['id']}"):
                        if ("edit_question_id" not in st.session_state or 
                            st.session_state["edit_question_id"] != row['id']):
                            st.session_state["edit_question_id"] = row['id']
                            st.session_state["edit_question_text"] = row['question']
                            st.session_state["edit_answer_text"] = row['answer']
                        st.rerun()

                # --- Remove question ---
                with col3:
                    if st.button("🗑️ Remove question", key=f"remove_{row['id']}"):
                        supabase.table("questions").delete().eq("id", row['id']).execute()
                        supabase.table("reviews").delete().eq("question_id", row['id']).execute()
                        st.success("Question removed.")
                        st.rerun()

                # --- Edit form ---
                if st.session_state.get("edit_question_id") == row['id']:
                    with st.form(key=f"edit_form_{row['id']}"):
                        new_q = st.text_area("Edit Question", value=st.session_state.get("edit_question_text", row['question']))
                        new_a = st.text_area("Edit Answer", value=st.session_state.get("edit_answer_text", row['answer']))
                        submitted = st.form_submit_button("Save Changes")
                        cancel = st.form_submit_button("Cancel")
                        if submitted:
                            supabase.table("questions").update({
                                "question": new_q,
                                "answer": new_a
                            }).eq("id", row['id']).execute()
                            st.success("Question updated.")
                            del st.session_state["edit_question_id"]
                            st.rerun()
                        elif cancel:
                            del st.session_state["edit_question_id"]
                            st.rerun()

# --- Tab 4: Add Question ---
with tab4:
    st.markdown(
        """
        <small>
        <b>How it works:</b><br>
        - When you add a question, it will be scheduled for review today.<br>
        - If you mark it as done, it will be shown again after 3 days.<br>
        - Each time you complete a review, the interval doubles: 3 days, then 6, then 12, and so on.<br>
        - If you don't click "Mark as reviewed", the question will continue to appear in the “To Review Today” list, even when the date rolls over to the next day.
        </small><br>
        """,
        unsafe_allow_html=True
    )
    st.write("")  # Add space
    q = st.text_area("Enter Question", placeholder="[TOPIC] Question")
    a = st.text_area("Enter Answer", placeholder="Paste the answer here")
    if st.button("Add"):
        if q and a:
            add_question(q, a)
            st.success("Question added! It will appear in today's review and follow the spaced repetition schedule (3, 6, 12 days, etc).")
        else:
            st.warning("Please fill both question and answer.")
