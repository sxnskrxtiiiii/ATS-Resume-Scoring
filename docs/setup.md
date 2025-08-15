⚙️ Setup & Installation
This guide helps run the ATS Resume Scoring System locally with the backend API and the Streamlit frontend.

1) ✅ Prerequisites
🐍 Python 3.10+

📦 pip and virtualenv

🔧 Git

🐳 Docker & Docker Compose (optional)

2) 📥 Clone and enter the project
bash
git clone <your-repo-url>.git
cd <your-repo-folder>
3) 🧪 Create and activate a virtual environment
bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
4) 📚 Install dependencies
bash
pip install -r requirements.txt
5) 🔐 Environment variables (.env)
Create a file named .env in the project root:

text
# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=5000
BACKEND_URL=http://localhost:5000

# Database
DB_URI=mongodb://localhost:27017
DB_NAME=atsdb

# Optional model/provider keys
# GROQ_API_KEY=...
Notes:

BACKEND_URL must match the value used in streamlit_app/app.py.

DB_URI/DB_NAME should point to a running database.

6) 🚀 Start the backend API
bash
python main.py
Default URL: http://localhost:5000

7) 🖥️ Start the Streamlit frontend
Open a new terminal (keep backend running), re-activate venv, then:

bash
streamlit run streamlit_app/app.py
Default URL: http://localhost:8501

8) 🐳 Optional: Dockerized run
bash
docker compose up --build
Builds and starts services as defined in docker-compose.yml.

9) 🔎 Verify the basic workflow
Open Streamlit UI.

Go to “📄 Upload JD” and submit a JD (paste or file).

Go to “📑 Upload Resume & Get Score,” upload resume, enter job role, click “Score Resume.”

Confirm:

🎯 Metrics: Overall, Keywords, Formatting, Grammar, JD Match.

🥧 Pie chart shows when JD requirements exist.

💡 Recommendations display actionable tips.

10) 🧩 Common issues & quick fixes
❌ Frontend cannot reach backend

Check BACKEND_URL in .env and in streamlit_app/app.py.

Ensure backend is running and ports match.

🔄 History not refreshing

Refresh Dashboard; ensure GET calls include a cache-buster param.

🗄️ Database connection errors

Verify DB_URI/DB_NAME and that the DB service is running.