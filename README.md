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

**ngrok & GitHub Webhook**

Follow these steps to expose your local FastAPI app to GitHub using `ngrok` and register the webhook.

- **Install ngrok (if needed)**:

```bash
# Install from https://ngrok.com/download
# Then authenticate once:
ngrok config add-authtoken <your-ngrok-authtoken>
```

- **Start the tunnel (forward port 8000)**:

```bash
ngrok http 8000
# Example output: Forwarding https://example.ngrok-free.app -> http://localhost:8000
```

- **Set the GitHub webhook Payload URL** (exactly):

```
https://<your-ngrok-domain>.ngrok-free.app/github/webhook
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

- Check the public ngrok tunnel:

```bash
curl https://<your-ngrok-domain>.ngrok-free.app/
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
  - The ngrok URL is not reachable. Restart `ngrok http 8000` and update the Payload URL in GitHub.
  - Make sure ngrok is still running and shows an active `Forwarding` URL.

- If the app returns `401 Invalid signature` in your terminal or GitHub deliveries:
  - Confirm `GITHUB_WEBHOOK_SECRET` in your `.env` matches the webhook Secret configured in GitHub.
  - Ensure there are no stray leading/trailing spaces in `.env`.

- If you do not see any logs when creating a PR:
  - Confirm the webhook `Recent deliveries` page shows a delivery for `pull_request` and inspect its response code and body.
  - Confirm `uvicorn` is running in the terminal where you are watching logs.
  - If the tunnel URL changed, update GitHub and retry.

**Advanced: send a signed test request from your machine**

Generate `X-Hub-Signature-256` for a payload using Python and send it to the public ngrok URL:

```python
import hmac, hashlib, requests
secret = b"YOUR_SECRET"
payload = b'{"action":"ping"}'
sig = hmac.new(secret, payload, hashlib.sha256).hexdigest()
headers = {
    "X-Hub-Signature-256": f"sha256={sig}",
    "X-GitHub-Event": "ping",
    "Content-Type": "application/json",
}
response = requests.post(
    "https://<your-ngrok-domain>.ngrok-free.app/github/webhook",
    data=payload,
    headers=headers,
)
print(response.status_code, response.text)
```

Expected output:

```text
200 {"status":"pong"}
```

## Example Workflow

The screenshots below show the review workflow from webhook processing through the GitHub pull request comment.

### Webhook review logs

<img width="1241" height="360" alt="Screenshot 2026-09-05 175445" src="https://github.com/user-attachments/assets/b35fa656-536a-4e1c-ae3b-99d0aad5d0c8" />


### Creating a pull request

<img width="1340" height="456" alt="Screenshot 2026-09-05 175332" src="https://github.com/user-attachments/assets/cbfe17a5-bbe7-419d-a821-1270d3252241" />


### Automated review comment

<img width="1331" height="594" alt="Screenshot 2026-09-05 174738" src="https://github.com/user-attachments/assets/74b2d9a7-8f3d-48f1-a6a9-afc4d3416716" />


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

6. If you want GitHub to send webhook events to your local machine, start `ngrok` (see the ngrok section) and update the GitHub webhook `Payload URL` to:

```
https://<your-ngrok-domain>.ngrok-free.app/github/webhook
```

7. Create a pull request in your repository and watch the terminal where `uvicorn` is running — you should see the webhook logs and diff parsing output.

Troubleshooting notes:

- If GitHub deliveries show `503`, restart ngrok and update the webhook URL.
- If you receive `401 Invalid signature`, ensure the webhook secret in GitHub matches `GITHUB_WEBHOOK_SECRET` and remove any leading/trailing spaces in `.env`.
