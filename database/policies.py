policy = {
"industries": {
"software engineering": {"keywords": ["python", "java", "git", "docker", "apis"], "boost": 2},
"data science": {"keywords": ["python", "pandas", "sql", "ml", "scikit"], "boost": 2},
"cloud": {"keywords": ["aws", "azure", "gcp", "kubernetes", "terraform"], "boost": 2},
"frontend": {"keywords": ["javascript", "react", "html", "css", "typescript"], "boost": 2},
"backend": {"keywords": ["python", "node", "java", "sql", "microservices"], "boost": 2},
},
"jd_specific": {
"must_have_skills_match": 4, # if >=70% must-have coverage
"degree_required_match": 2, # if degree meets/exceeds requirement
"exp_meets_or_exceeds": 2 # if experience >= required
}
}