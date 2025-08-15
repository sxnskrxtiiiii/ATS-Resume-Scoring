import streamlit as st
import pandas as pd
import plotly.express as px

def show_score_chart(score_dict):
    """Displays bar chart of main scoring categories."""
    # Filter only numeric scores
    filtered_scores = {k: v for k, v in score_dict.items()
                       if isinstance(v, (int, float)) and k not in ["confidence_interval"]}
    
    if not filtered_scores:
        st.info("No numeric scores available to plot.")
        return

    df = pd.DataFrame(list(filtered_scores.items()), columns=["Metric", "Score"])
    fig = px.bar(df, x="Metric", y="Score", range_y=[0, 100],
                 title="ATS Scoring Breakdown", text="Score")
    st.plotly_chart(fig, use_container_width=True)

def show_suggestions(data):
    st.subheader("🔍 Missing Skills")
    st.write(data.get("missing_skills", []))

    st.subheader("📝 Missing Keywords")
    st.write(data.get("missing_keywords", []))

    st.subheader("🎯 Gaps")
    st.json(data.get("gaps", {}))

    st.subheader("💡 Tips")
    for tip in data.get("tips", []):
        st.write(f"- {tip}")

def show_job_recommendations(df):
    """Show recommended jobs as a table."""
    if df.empty:
        st.info("No job recommendations found.")
    else:
        st.dataframe(df)
