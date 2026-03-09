import streamlit as st
import pandas as pd
import sqlite3
from google import genai
import re

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="AI Business Intelligence Dashboard",
    layout="wide"
)

# -----------------------------
# Professional Dark Theme
# -----------------------------
st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Open Sans', sans-serif;
    font-size:23px;
}

/* Main background */
[data-testid="stAppViewContainer"]{
background-color:#0b1220;
color:white;
}

/* Sidebar */
[data-testid="stSidebar"]{
background-color:#111827;
}

/* Company panel */
.company-box{
text-align:center;
padding:20px;
border-bottom:1px solid #374151;
margin-bottom:20px;
}

/* Logo */
.company-logo{
width:100px;
transition:0.3s;
}

.company-logo:hover{
transform:scale(1.1);
}

/* Company name */
.company-name{
font-size:24px;
font-weight:700;
color:#f43f5e;
}

/* Main title */
.main-title{
font-size:46px;
font-weight:800;
}

/* Section titles */
.section-title{
font-size:28px;
font-weight:700;
margin-top:30px;
}

/* Chart titles */
.metric-title{
font-size:20px;
font-weight:700;
}

/* Card layout */
.card{
background:#111827;
padding:20px;
border-radius:14px;
box-shadow:0px 5px 20px rgba(0,0,0,0.4);
margin-bottom:20px;
}

/* Info box */
[data-testid="stInfo"]{
background:#1f2937;
border-radius:10px;
}

/* Inputs */
input{
font-size:18px !important;
}

</style>
""", unsafe_allow_html=True)

# -----------------------------
# Sidebar Branding
# -----------------------------
st.sidebar.markdown("""
<div class="company-box">

<img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
class="company-logo">

<div class="company-name">
Team Jarvis
</div>

<p style="font-size:13px;color:#9ca3af;">
AI Business Intelligence
</p>

</div>
""", unsafe_allow_html=True)

# -----------------------------
# Page Title
# -----------------------------
TITLE_SIZE = 55   # change this number anytime
# st.markdown('<p class="main-title"> AI Business Intelligence Dashboard</p>', unsafe_allow_html=True)
st.markdown(
f"<h1 style='font-size:{TITLE_SIZE}px; font-weight:800;'>AI Business Intelligence Dashboard</h1>",
unsafe_allow_html=True
)

st.caption(
"Ask business questions and automatically generate SQL queries, explanations, and dashboards."
)

# -----------------------------
# Sidebar Dataset Upload
# -----------------------------
st.sidebar.header("📂 Upload Dataset")

uploaded_file = st.sidebar.file_uploader(
    "Upload Dataset",
    type=["csv","xlsx"]
)

# -----------------------------
# Load Dataset
# -----------------------------
if uploaded_file is not None:

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file,encoding="latin1")
    else:
        df = pd.read_excel(uploaded_file)

    dataset_name = uploaded_file.name.split(".")[0]
    dataset_name = dataset_name.replace(" ","_").lower()

    st.sidebar.success("Dataset uploaded")

else:
    df = pd.read_csv("insurance_claims.csv",encoding="latin1")
    dataset_name = "insurance_claims"
    st.sidebar.info("Using default dataset")

st.sidebar.write(f"Active Table: **{dataset_name}**")

# -----------------------------
# Dataset Preview
# -----------------------------
with st.expander("🔎 Preview Dataset"):
    st.dataframe(df.head(),use_container_width=True)
    st.write("Rows:",df.shape[0]," Columns:",df.shape[1])

# -----------------------------
# Create SQL Database
# -----------------------------
conn = sqlite3.connect(":memory:")
df.to_sql(dataset_name,conn,index=False,if_exists="replace")

# -----------------------------
# Gemini API
# -----------------------------
client = genai.Client(api_key="My-api-key-here")

# -----------------------------
# Ask Question
# -----------------------------
st.markdown('<p class="section-title">Ask a Business Question</p>', unsafe_allow_html=True)

user_query = st.text_input("Example: Show top insurers by claims paid amount")

# -----------------------------
# Query Processing
# -----------------------------
if user_query:

    with st.spinner("Generating insights..."):

        columns = ", ".join(df.columns)

        # -----------------------------
        # Validate Query
        # -----------------------------
        validation_prompt = f"""
Dataset table: {dataset_name}
Columns: {columns}

User question:
{user_query}

Return ONLY:
VALID
or
INVALID
"""

        validation = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=validation_prompt
        )

        if "INVALID" in validation.text.upper():
            st.warning("⚠ Query cannot be answered using this dataset.")
            st.stop()

        # -----------------------------
        # SQL Generation
        # -----------------------------
        sql_prompt = f"""
Convert the question to SQL.

Table: {dataset_name}

Columns:
{columns}

Return SQL only.

Question:
{user_query}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=sql_prompt
        )

        sql_query = response.text
        sql_query = sql_query.replace("```sql","").replace("```","").strip()

        match = re.search(r"(SELECT .*?;)", sql_query, re.I|re.S)

        if match:
            sql_query = match.group(1)

        # -----------------------------
        # Execute SQL
        # -----------------------------
        try:

            result = pd.read_sql_query(sql_query,conn)

            # -----------------------------
            # Explanation
            # -----------------------------
            explanation_prompt = f"""
Explain the SQL in simple business language.

SQL:
{sql_query}

Result:
{result.head().to_string(index=False)}
"""

            explanation = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=explanation_prompt
            )

            # -----------------------------
            # SQL + Explanation Layout
            # -----------------------------
            col1,col2 = st.columns(2)

            with col1:
                st.markdown('<p class="section-title">Generated SQL</p>', unsafe_allow_html=True)
                st.code(sql_query,language="sql")

            with col2:
                st.markdown('<p class="section-title">Query Explanation</p>', unsafe_allow_html=True)
                st.info(explanation.text)

            # -----------------------------
            # Query Result
            # -----------------------------
            st.markdown('<p class="section-title">Query Result</p>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.dataframe(result,use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # -----------------------------
            # Dashboard
            # -----------------------------
            st.markdown('<p class="section-title">Auto Generated Dashboard</p>', unsafe_allow_html=True)

            numeric_cols = result.select_dtypes(include=['number']).columns.tolist()
            category_cols = [c for c in result.columns if c not in numeric_cols]

            if category_cols:

                category = category_cols[0]

                charts = numeric_cols

                for i in range(0,len(charts),2):

                    col1,col2 = st.columns(2)

                    for j,col in enumerate([col1,col2]):

                        if i+j < len(charts):

                            metric = charts[i+j]

                            title = metric.replace("_"," ").title()

                            chart_data = result[[category,metric]].dropna()

                            with col:

                                st.markdown(
                                f'<p class="metric-title">{title}</p>',
                                unsafe_allow_html=True
                                )

                                if category.lower()=="year":
                                    chart_data=chart_data.sort_values(by=category)
                                    st.line_chart(chart_data.set_index(category))

                                elif "ratio" in metric.lower():

                                    st.plotly_chart({
                                        "data":[{
                                            "labels":chart_data[category],
                                            "values":chart_data[metric],
                                            "type":"pie"
                                        }]
                                    })

                                else:
                                    st.bar_chart(chart_data.set_index(category))

        except Exception as e:

            st.error("SQL Execution Error")
            st.write(e)