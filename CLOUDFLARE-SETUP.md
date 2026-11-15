# Flask and D1 on Cloudflare

The `cloudflare-deployment` branch runs the existing student and teacher interfaces with Flask routes backed by D1. The admin screen replaces Flask-Admin's SQLAlchemy model views with D1-backed user, course, and enrollment management. `app.py` and `static/` preserve the original application for reference. Wrangler requires the original `requirements.txt` to be renamed to `requirements.legacy.txt`; Worker dependencies are in `pyproject.toml`.

## Local setup

```sh
uv sync
# Only if .dev.vars does not already exist:
printf 'SESSION_SECRET=%s\n' "$(openssl rand -hex 32)" > .dev.vars
uv run pywrangler d1 execute lab08-enrollment --local --file=migrations/0001_initial.sql
uv run pywrangler d1 execute lab08-enrollment --local --file=dev/seed-demo.sql
uv run pywrangler dev --local
```

Run the schema and seed only against an empty local database. The seed reproduces the original repository's example users, classes and enrollments. Its shared demo password is `password`; **use the demo seed only for throwaway data**. The local secret and local database are ignored by Git. On this checkout, the local database and secret are already set up.

Open http://localhost:8787/. Examples: `cnorris` is a student, `ahepworth` is a teacher, and `admin` is an administrator. Run `python3 tests/integration.py` against the running local server to exercise the three roles; it expects the example seed and changes local test records.

## Hosted deployment

The demo is live at https://lab08-miniproject.zacharyamith.workers.dev. The hosted `lab08-enrollment` D1 database contains the `andres` and `zachary` admin accounts and no courses or enrollments. A Worker secret named `SESSION_SECRET` is configured. Both admin accounts use `password`; each stored PBKDF2-SHA256 hash has its own salt. The demo seed is intentionally public and is suitable only for throwaway data.

Deploy changes with `uv run pywrangler deploy`. Do not apply the schema or demo seed again to the existing hosted database; those commands are intended for an empty database. The D1 database ID in `wrangler.toml` belongs to the Cloudflare account used for this setup; replace it for a different account.

Workers Web Crypto limits PBKDF2 to 100,000 iterations, so the Worker uses that value and verifies PBKDF2-SHA256 hashes with up to 100,000 iterations. The original Flask application defaults to scrypt hashes, which this Worker cannot verify; imported accounts with those hashes or higher PBKDF2 iteration counts need a password reset or conversion in a trusted environment with the plaintext password.
