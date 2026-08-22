# code-review-agent

Minimal scaffolding for a GitHub code review assistant.

Structure created:

- app/
  - api/
  - core/
  - github/
  - services/

To run the minimal entrypoint:

```bash
python -m app.main
```

## Logging

This project writes runtime logs to a `logs/` folder by default and also
emits logs to stdout so they are visible when running under Uvicorn. The
`logs/` directory is ignored by Git (see `.gitignore`).

Defaults:

- Log file: `logs/app.log`
- Rotation: 5 MB per file, 5 backups

Configuration:

- Use the `LOG_DIR` environment variable to change the logs directory.
- Set the root logging level or the `code_review_agent.webhook` logger level
  via Python logging configuration or environment-driven config.

Production notes:

- In containerized/managed environments prefer writing logs to stdout/stderr
  and let the platform collect them (12-factor logging).
- Consider using structured JSON logs and a central log aggregator (ELK,
  Datadog, Cloud Logging) for production systems.

See `logging.conf.example` for an example configuration you can load with
`logging.config.dictConfig`.

**Local Tunnel & GitHub Webhook**

Follow these steps to expose your local FastAPI app to GitHub using `localtunnel` and register the webhook.

- **Install localtunnel (if needed)**:

```bash
npm install -g localtunnel
```

- **Start the tunnel (forward port 8000)**:

```bash
lt --port 8000
# Example output: your url is: https://fast-foxes-hear.loca.lt
```

- **Set the GitHub webhook Payload URL** (exactly):

```
https://<your-lt-id>.loca.lt/github/webhook
```

- **Webhook settings in GitHub**:
  - Content type: `application/json`
  - Secret: use the same value as `GITHUB_WEBHOOK_SECRET` in your local `.env`
  - Events: enable **Pull requests** (or choose "Send me everything" during testing)
  - Save the webhook

- **Run the app** (if not already running):

```bash
uvicorn app.main:app --reload
```

- **Verify locally**:
  - Check the health route:

```bash
curl http://127.0.0.1:8000/
# -> {"status":"running"}
```

- Quick local POST to the webhook path (no signature header will return `401`):

```bash
curl -v -X POST http://127.0.0.1:8000/github/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"opened","pull_request":{"number":1},"repository":{"owner":{"login":"you"},"name":"repo"}}'
```

- **Test with GitHub**:
  - Create or open a pull request in the repo.
  - In the app terminal you should see debug logs like `Incoming GitHub webhook request` and `GitHub event: pull_request` followed by `Files Changed` and `Diffs parsed:` entries.

**Troubleshooting**

- If GitHub shows `503 Service Unavailable` for deliveries:
  - The tunnel URL is not reachable. Restart `lt` and update the Payload URL in GitHub.
  - Make sure the tunnel command is still running and shows the active URL.

- If the app returns `401 Invalid signature` in your terminal or GitHub deliveries:
  - Confirm `GITHUB_WEBHOOK_SECRET` in your `.env` matches the webhook Secret configured in GitHub.
  - Ensure there are no stray leading/trailing spaces in `.env`.

- If you do not see any logs when creating a PR:
  - Confirm the webhook `Recent deliveries` page shows a delivery for `pull_request` and inspect its response code and body.
  - Confirm `uvicorn` is running in the terminal where you are watching logs.
  - If the tunnel URL changed, update GitHub and retry.

**Advanced: send a signed test request from your machine**

Generate `X-Hub-Signature-256` for a payload using Python and send it to the public tunnel URL (replace `SECRET` and `URL`):

```bash
python - <<PY
import hmac, hashlib, requests
secret = b"YOUR_SECRET"
payload = b'{"action":"opened"}'
sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
headers = {"X-Hub-Signature-256": f"sha256={sig}", "Content-Type": "application/json"}
print(requests.post("https://<your-lt-id>.loca.lt/github/webhook", data=payload, headers=headers).status_code)
PY
```

## Running Locally

Follow these steps to run the application on your development machine.

1. Create and activate a virtual environment

```bash
# Create venv
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (cmd.exe)
venv\Scripts\activate.bat

# Activate (macOS / Linux)
source venv/bin/activate
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Configure environment variables

Create a `.env` file at the repository root (or edit the existing one) and set these values:

```env
GITHUB_TOKEN=ghp_your_token_here
GITHUB_WEBHOOK_SECRET=your_webhook_secret_here
GITHUB_API=https://api.github.com
```

Make sure there are no extra spaces around the values.

4. Start the FastAPI app

```bash
uvicorn app.main:app --reload
```

5. Verify the app is running

```bash
curl http://127.0.0.1:8000/
# -> {"status":"running"}
```

6. If you want GitHub to send webhook events to your local machine, start `localtunnel` (see the Local Tunnel section) and update the GitHub webhook `Payload URL` to:

```
https://<your-lt-id>.loca.lt/github/webhook
```

7. Create a pull request in your repository and watch the terminal where `uvicorn` is running — you should see the webhook logs and diff parsing output.

Troubleshooting notes:

- If GitHub deliveries show `503`, restart the tunnel and update the webhook URL.
- If you receive `401 Invalid signature`, ensure the webhook secret in GitHub matches `GITHUB_WEBHOOK_SECRET` and remove any leading/trailing spaces in `.env`.
