💡 Recommendations
This document describes how improvement suggestions are generated from resume/JD analysis and how they map to UI elements.

🧠 Sources of Suggestions
Missing keywords: JD.must_have_skills − resume.skills

Desired skills gap: JD.desired_skills − resume.skills (lower priority)

Formatting violations: collected in formatting_score computation

Grammar flags: grammar_signals from parsing/linters

Experience gap: max(0, JD.min_years − resume.total_years)

Structure gaps: missing sections (Summary, Skills, Projects, Experience, Education)

📜 Suggestion Types
Keywords & Skills

Add the following missing must-have skills: [...]

Weave these keywords naturally into Experience bullets and Projects.

Formatting & Structure

Use consistent bullet symbols and indentation.

Keep to 1–2 pages; standard margins; clear section headings.

Order: Summary → Skills → Experience → Projects → Education.

Grammar & Clarity

Use action verbs; remove first‑person pronouns.

Quantify outcomes (X% improvement, $Y saved, Z users).

Experience Alignment

Highlight role‑relevant projects; surface most relevant technologies.

Address experience shortfall by emphasizing internships, freelance, or coursework.

🔗 Data → Text Mapping
For each missing skill s in missing_skills, create: “Add s to your Skills or a relevant bullet.”

For each formatting violation v, map to a short directive.

If experience_shortfall_years > 0: “Address an experience gap of N years by …”

🧾 Example API Fragment
json
{
  "recommendations": {
    "missing_keywords": ["pandas","docker"],
    "format_suggestions": ["Use consistent bullets", "Add section headings"],
    "grammar_issues": [],
    "resume_enhancement_tips": [
      "Quantify achievements with metrics.",
      "Add a Projects section highlighting JD‑relevant skills."
    ]
  }
}
🖥️ UI Placement
Score page: Recommendations card below metrics and pie chart.

Dashboard: optional preview in recent runs; expand for details.

🧯 Edge Cases
No JD provided: show general formatting/structure tips; omit missing JD keywords.

Very high scores: provide fine‑tuning suggestions instead of generic tips.

Empty or corrupted resume: return API error; no recommendations.