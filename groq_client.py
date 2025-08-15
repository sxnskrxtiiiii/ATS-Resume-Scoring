# groq_client.py
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("Missing GROQ_API_KEY in environment variables.")

client = Groq(api_key=groq_api_key)

def get_resume_score(prompt):
    response = client.chat.completions.create(
        model="llama3-8b-8192",  # You can change to a faster/bigger Groq model
        messages=[
            {"role": "system", "content": "You are an ATS resume scoring assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content
