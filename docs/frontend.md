🖥️ Frontend (Streamlit) Guide
This guide covers the Streamlit pages, user flows, and visual components.

📄 Pages
Dashboard

Shows recent history and KPIs.

Actions: filter by resume_hash, paginate.

Upload JD

Upload a JD file or paste text.

On submit, shows parsed fields and jd_hash.

Upload Resume & Get Score

Upload a resume (PDF/DOCX/TXT).

Optional: paste JD text or rely on latest JD.

Displays metrics (Overall, Keywords, Formatting, Grammar, JD Match).

Shows Skills Coverage pie when JD must‑have skills exist.

Recommendations card appears below the metrics.

Suggestions

Fetches improvement details for a selected resume_hash.

Jobs

Lists open relevant jobs suggested from the database.

CSV export option.

Reports

KPIs, recent scores, recent runs, average categories, top missing JD skills.

🧩 Components
Metrics row: st.metric for Overall and category scores.

Pie chart: Plotly pie for skills matched vs missing.

Tables: st.dataframe for history, jobs, and reports.

Download buttons: st.download_button for JSON/CSV.

🔁 Reruns & Caching
Use explicit “Score Resume” and refresh buttons to avoid stale state.

If visuals don’t update, hard refresh the browser.

🖼️ Screenshots (place in images/)
images/dashboard.png

images/score_page.png

images/reports.png

🧯 Error Handling
Clear toast/alert when:

No JD provided but JD‑specific charts requested.

Unsupported file type.

Backend unreachable (show BACKEND_URL hint).

♿ Accessibility & UX Notes
Keep consistent headings and spacing.

Provide text alternatives for icons/emojis.

Ensure color contrasts meet minimum accessibility guidelines.