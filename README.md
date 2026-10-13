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
With Docker, this folder is mounted as persistent storage using the command below.

Pressing Ctrl+C during screening or retries cancels the entire batch and returns
to the main menu. Its job, candidate results, and debug JSON are saved only after
screening and retry choices finish. Cancellation leaves previous batches untouched.
To try again, select a new batch and screen the folder from the beginning.

## Run with Docker

Start Docker Desktop with Linux containers enabled. Run these commands in
PowerShell from the project folder.

Build the image:

```powershell
docker build -t resume-screener .
```

Keep `OPENROUTER_API_KEY=your_key_here` in your local `.env` file. Docker reads it
when starting the container; the file is excluded from the image and build context.
Put PDF/DOCX resumes in the local `resume/` folder, then start the application:

```powershell
New-Item -ItemType Directory -Path data,resume -Force | Out-Null
docker run --rm -it --init --env-file .env --mount "type=bind,source=$((Get-Location).Path)/data,target=/app/data" --mount "type=bind,source=$((Get-Location).Path)/resume,target=/app/resume,readonly" resume-screener
```

Enter `/app/resume` when the application asks for the resume folder. The container
uses Linux paths; your Windows folder path is supplied by the mount command.
The resume mount is read-only. Saved CSVs and debug JSON appear in your local
`data/` folder and remain there when the container exits. Use the same run command
to reopen the application and view or review saved results.

The application is a terminal program, so it uses `-it` and needs no published
ports. `--rm` removes the stopped container; it does not remove the mounted data.
If Docker reports that it cannot connect to the engine, start Docker Desktop and
wait until the Linux engine is ready.

The build installs the four direct dependencies from `requirements.txt` and copies
the five Python application modules. Local API keys, resumes, generated data, the
virtual environment, and local tests are excluded from the image.

## Run locally

Python 3.10 or newer is required; the Docker image uses Python 3.12.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe main.py
```

Local testing, when `test_project.py` is available in your checkout:

```powershell
.venv/Scripts/python.exe -B test_project.py
```

Tests use temporary data and simulated API responses. They do not read your API
key or call OpenRouter.
