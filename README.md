# UzSite (Django + Docker MVP)

MVP features:
- Registration + login/logout (Django auth)
- Blog-style front page: one featured **Latest** post + a grid of other posts (sorted newest first)
- Admin interface for managing posts

## Run locally (no Docker)

```bash
cd /home/ubuntu/uzsite
. .venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Open: http://localhost:8000

## Run with Docker (recommended for deployment)

Install Docker first (Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# log out / log back in
```

Then run:

```bash
cd /home/ubuntu/uzsite
cp .env.example .env.docker
# edit .env.docker (set DJANGO_SECRET_KEY + passwords)

docker compose up --build
```

Open: http://localhost:8000

## Create your first blog post

1. Go to `/admin/`
2. Create a BlogPost with:
   - `status = Published`
   - `published_at` set
3. It will appear on the home page. The newest post is featured as **Latest**.

## Notes on “secure by default”

- Secrets and database config come from environment variables (`.env*` files).
- `DEBUG` defaults to off unless explicitly enabled.
- `SECURE_*` flags are configurable via env for when you put this behind HTTPS (e.g., nginx/Traefik).

Next step ideas (when you expand toward ClickUp/TradeZella/crypto advisory):
- Organizations/teams, roles, and permissions
- Task + project models, comments, activity feed
- Advisory “signals” / research posts with subscriptions
- Audit logging and 2FA
