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

The OOP test suite in `tests/` uses fixed sample AI responses and a mocked API
client, so it needs no API key or internet connection.

Locally:

```powershell
python -B -m unittest discover -s tests -t . -v
```

Inside the built Docker image, with networking disabled:

```powershell
docker build -t resume-screener-ui .
docker run --rm --network none --entrypoint python resume-screener-ui -B -m unittest discover -s tests -t . -v
```

## Continuous Integration

GitHub Actions (`.github/workflows/ci.yml`) runs automatically on every push to
any branch and on every pull request into `main`. It has two jobs:

1. **Unit tests**: installs `requirements.txt` on Python 3.12 and runs the test suite.
2. **Docker build and tests**: builds the Docker image and runs the same tests
   inside the container with networking disabled.

Results appear in the repository's **Actions** tab and as checks on pull requests.
