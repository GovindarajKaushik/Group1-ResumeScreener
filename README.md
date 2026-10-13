# Resume Screener

Run these commands in PowerShell from the project folder. Put PDF/DOCX resumes
in `resume/` and set your key in a local `.env` file without `export`:

```dotenv
OPENROUTER_API_KEY=your_key_here
```

## Run locally

Use Python 3.10 or newer:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe main.py
```

Enter `resume` when asked for the resume folder, then press Enter to continue.

## Run with Docker

Start Docker Desktop with Linux containers enabled:

```powershell
docker build -t resume-screener .
New-Item -ItemType Directory -Path data,resume -Force | Out-Null
docker run --rm -it --init --env-file .env --mount "type=bind,source=$((Get-Location).Path)/data,target=/app/data" --mount "type=bind,source=$((Get-Location).Path)/resume,target=/app/resume,readonly" resume-screener
```

Enter `/app/resume` when asked for the resume folder, then press Enter to continue.
Rebuild the image after changing the code or test script.

## Saved data

Files are stored in the local `data/` folder and remain after the container exits:

- `candidate_results.csv`: candidate scores, evidence, and recruiter decisions.
- `jobs.csv`: job requirements.
- `audit_log.csv`: recorded actions and timestamps.
- `resume_results.json`: debug output.

Open the CSV files in Excel. Close them before saving updates in the application.

## Run tests

The logic tests use fixed sample AI responses and require no API key or connection.

Locally:

```powershell
python -B test_logic.py
```

Inside the built Docker image, with networking disabled:

```powershell
docker run --rm --network none resume-screener python -B test_logic.py
```
