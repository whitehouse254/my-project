import app
jobs = app.fetch_jsearch_jobs("software engineer", "USA", 150)
print(f"Fetched {len(jobs)} jobs")
if jobs:
    print("Sample job:", jobs[0]['title'])