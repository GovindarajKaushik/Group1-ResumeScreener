# Group1-ResumeScreener
Resume Screener project using python and AI API.

Generated files are stored in `data/` beside the Python files. The application
creates this folder when it first saves data, even when launched from another
working directory.

```text
data/
    jobs.csv
    candidate_results.csv
    audit_log.csv
    resume_results.json
```

The CSV files hold jobs, screening results, recruiter decisions, and audit entries.
`resume_results.json` is debug output; scoring does not depend on it. Temporary
CSV files are written in this folder and removed after saving.

Generated data is excluded from Git. If upgrading an older checkout, move its
existing files listed above from the project root into `data/` before starting.
Do not overwrite files if the destination already contains saved data.
When Docker support is added, this folder can be mounted as persistent storage.
