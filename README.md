# Spaced Repetition Learning App

Hi. I made this interactive learning tool designed to help me study using the **spaced repetition technique**. I use this to review python syntax, but you can use it for anything (biology, history, or whatever). 
I built this using **Streamlit** and **Supabase** for cloud database storage. Here's the list of features I made:

## Features

### 1. Add Your Own Questions & Answers

* Enter a question and its answer
* It appears in **today's review list**
* Once marked reviewed, it reappears after **3, 6, 12 days**, and so on
* This increasing interval follows a **spaced repetition schedule**

<img width="628" height="713" alt="image" src="https://github.com/user-attachments/assets/5b1705fa-c70e-4d52-a879-325893ad21b2" />  

---

### 2. Manage Your Question Bank

* View all added questions
* Edit or remove questions anytime

<img width="681" height="800" alt="image" src="https://github.com/user-attachments/assets/44806084-b1c3-42ea-85ab-5fcc0fc462a8" />  

---

### 3. Track Your Progress

* Daily review count visualized like **GitHub contribution heatmaps**
* Check which questions you reviewed on a specific date

<img width="662" height="700" alt="image" src="https://github.com/user-attachments/assets/f5edc0c1-61be-4f9b-995e-db968d519cb4" />  

---

### 4. Daily Review List

* View all questions due for today
* Start reviewing with a single click

<img width="634" height="704" alt="image" src="https://github.com/user-attachments/assets/2864f712-9730-49b4-9814-a9cd2e963438" />  

---

### 5. Active Review Mode

* Write your answer
* Click **“Reveal Answer”** to check correctness
* Mark as reviewed to schedule it for the next interval

<img width="661" height="735" alt="image" src="https://github.com/user-attachments/assets/c4d8defe-11ec-464d-a934-0760e84f7cb7" />  

---

## Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io)
* **Database:** [Supabase](https://supabase.com) (PostgreSQL backend)
* **Visualization:** Plotly (for daily activity heatmap)

This is the MVP, so I haven't made account login yet to track it by user, but if you want to use this, you can easily setup yourself. Here's the steps:

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/spaced-repetition-learning-app.git
cd spaced-repetition-learning-app
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Supabase Secrets

Create `.streamlit/secrets.toml`:

```toml
SUPABASE_URL = "supabase-project-url"
SUPABASE_KEY = "anon-key"
```

### 4. Run the App

```bash
streamlit run streamlit_app.py
```

If using local: $env:LOCAL="1" streamlit run streamlit_app.py

## Deployment

* Hosted on **Streamlit Cloud**
* Uses **Supabase** for data storage
