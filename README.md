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
