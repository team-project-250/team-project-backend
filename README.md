# Team Project — Backend

REST API for the Team Project — an equipment-rental service — built with **Django + Django REST Framework**.

Frontend repository: [`team-project-frontend`](https://github.com/glor1ee/team-project-frontend)

> **Status:** Stage 3 (core features) is complete — catalog, bookings, quick-booking,
> reviews, cities and all editable home/product-page content are live behind the API
> below. See [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md) for what's next (polish,
> testing, deploy).

---

## Tech stack

| Area | Choice |
| --- | --- |
| Language | Python 3.12+ |
| Framework | Django + Django REST Framework |
| Database | PostgreSQL |
| DB driver | psycopg 3 |
| Settings | django-environ (`.env`) |
| API schema | drf-spectacular (OpenAPI / Swagger) |
| Filtering | django-filter |
| CORS | django-cors-headers |
| WSGI server | Gunicorn (production) |
| Tests | pytest + pytest-django + pytest-cov |
| Lint / format | Ruff |
| Type checking | mypy |
| Image handling | Pillow |
| Hooks | pre-commit |
| CI | GitHub Actions |
| Deploy | Render |

---

## Getting started

### 1. Clone and enter the project

```bash
git clone https://github.com/glor1ee/team-project-backend.git
cd team-project-backend
```

### 2. Create a virtual environment

**Windows (PowerShell):**

```powershell
py -3 -m venv venv
venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements-dev.txt
```

Runtime-only dependencies live in `requirements.txt`; `requirements-dev.txt`
adds the test and lint tooling.

### 4. Create the environment file

```bash
cp .env.example .env
```

`.env` is git-ignored — never commit real secrets.

### 5. Start PostgreSQL

The repo ships a `docker-compose.yml` with a ready-to-use database that matches the
default `DATABASE_URL`:

```bash
docker compose up -d db
```

No Docker? Create a `easyrent` database in your own PostgreSQL instance and point
`DATABASE_URL` at it.

### 6. Apply migrations and create an admin user

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 6a. Load demo data (optional)

```bash
python manage.py seed_demo
```

Loads every app's fixtures (cities, categories, equipment, reviews, home/product
content) plus one demo booking, so the API and admin have real data to look at.
Safe to run repeatedly.

### 7. Run the server

```bash
python manage.py runserver
```

The API is available at <http://127.0.0.1:8000>, the admin at <http://127.0.0.1:8000/admin/>.

### 8. Install git hooks (optional but recommended)

```bash
pre-commit install
```

---

## API documentation

Generated automatically by drf-spectacular:

- Swagger UI — <http://127.0.0.1:8000/api/docs/>
- OpenAPI schema — <http://127.0.0.1:8000/api/schema/>

### Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/cities/` | List of active service cities with pickup point info |
| GET | `/api/cities/{slug}/` | Single city detail |
| GET | `/api/reviews/` | Published customer reviews, newest first (paginated) |
| GET | `/api/categories/` | Active equipment categories |
| GET | `/api/equipment/` | Equipment list — filter by `category`, `city`, `price_min`/`price_max`, `is_popular`, `availability` (`available`/`booked`); search via `search`; sort via `ordering` (`rating` default, `price_per_day`); 8 per page. Each item includes `availability: {status, available_from}` |
| GET | `/api/equipment/{slug}/` | Equipment detail — specs, gallery, included items, benefits, badges, `suitable_for`, `breadcrumbs`, available cities, `availability` |
| GET | `/api/equipment/{slug}/availability/?month=YYYY-MM` | Booked dates for that equipment in the given month (defaults to the current month) |
| GET | `/api/equipment/{slug}/related/?limit=` | "Інша техніка" — same category first, then filled with other active equipment (excludes the item itself); `limit` defaults to 3, capped at 12 |
| POST | `/api/bookings/quote/` | Price preview for equipment + dates + delivery method, no booking created |
| POST | `/api/bookings/` | Create a booking — requires `customer_name`, `customer_phone` (`+380XXXXXXXXX`), `customer_email`, dates, delivery/payment method; server computes the price and checks availability. 400 for invalid input, 409 if the equipment is already booked for those dates |
| GET | `/api/bookings/?phone=` | List that phone number's bookings, newest first (`phone` is required). Throttled to 30/hour per IP. |
| POST | `/api/bookings/{number}/cancel/` | Cancel a booking — body `{"phone": "..."}` must match; only `pending`/`confirmed` bookings with a future start date can be cancelled. Throttled to 10/hour per IP. |
| POST | `/api/callback-requests/` | "1-click" booking (a lead, not a reservation) — phone (`+380XXXXXXXXX`) + optional equipment/dates. 400 for bad phone/dates, 409 for a date conflict on the given equipment, 200 (not 201) if an identical unprocessed request already exists. Throttled to 5/hour per IP. |
| GET | `/api/content/hero/` | Home page hero section (title, subtitle, CTA, background image) — editable in admin |
| GET | `/api/content/about/` | "About EasyRent" section with its ordered feature list |
| GET | `/api/content/rental-steps/` | "How to rent" steps, active ones only, ordered |
| GET | `/api/content/rental-terms/` | "Rental terms" cards, active ones only, ordered |
| GET | `/api/content/delivery-payment/` | "Доставка і оплата" tab content on the product page (global, same for every product) |
| GET | `/api/content/settings/` | Company/bank details shown after choosing the IBAN transfer payment method |
| GET | `/api/home/` | Aggregates hero, about, rental steps/terms, settings, cities, categories, popular equipment and reviews into one response for the landing page |

Content sections (hero, about, rental steps/terms, delivery/payment, site settings)
are all editable through the Django admin — nothing on the home or product page is
hardcoded on the frontend.
`HeroSection`, `AboutSection` and `SiteSettings` are singletons (the admin hides
"Add" once a row exists).

See [`docs/BACKEND_ROADMAP.md`](docs/BACKEND_ROADMAP.md) for the full planned API.

---

## Environment variables

| Variable | Example | Description |
| --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` | Which settings module to load |
| `SECRET_KEY` | `dev-secret-change-me` | Django secret key |
| `DEBUG` | `True` | Debug mode — never `True` in production |
| `DATABASE_URL` | `postgres://postgres:postgres@localhost:5432/easyrent` | PostgreSQL connection string |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed frontend origins |
| `AWS_STORAGE_BUCKET_NAME` (+ `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, optional `AWS_S3_ENDPOINT_URL`, `AWS_S3_REGION_NAME`, `AWS_S3_CUSTOM_DOMAIN`) | `easyrent-media` | Production: S3-compatible bucket (AWS S3, Cloudflare R2, …) for uploaded images. Unset, uploads go to local disk, which Render wipes on every deploy |
| `NUM_PROXIES` | `1` | Production: reverse proxies in front of the app. Rate limiting takes the client IP from `X-Forwarded-For` using this; unset, the limits can be bypassed by spoofing the header |

All variables are documented in [`.env.example`](.env.example).

---

## Project structure

```
team-project-backend/
├── config/                     # project configuration
│   ├── settings/
│   │   ├── base.py             # shared settings, reads .env
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py                 # root URL conf (/admin/, /api/, schema)
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── catalog/        # categories, equipment, specs, badges, availability
│   ├── bookings/       # bookings, quick-booking (callback requests), pricing
│   ├── locations/      # cities/pickup points + the seed_demo command
│   ├── reviews/        # customer reviews (moderated)
│   └── content/        # editable home/product-page content + /api/home/
│       # each app: models.py / serializers.py / views.py / urls.py / admin.py,
│       # most also have services.py, fixtures/ and tests/
├── docs/
│   └── BACKEND_ROADMAP.md      # full milestone-by-milestone API plan
├── tests/                       # project-level smoke tests
├── manage.py
├── requirements.txt            # runtime dependencies
├── requirements-dev.txt        # + test & lint tooling
├── pyproject.toml              # tool configuration (ruff, mypy, pytest)
├── docker-compose.yml          # local PostgreSQL for development
└── render.yaml                 # Render deployment blueprint
```

---

## Development commands

| Command | What it does |
| --- | --- |
| `python manage.py runserver` | Run the dev server |
| `python manage.py makemigrations` | Create migrations from model changes |
| `python manage.py migrate` | Apply migrations |
| `pytest` | Run the test suite |
| `pytest --cov --cov-report=term-missing` | Tests with a coverage report |
| `ruff check .` | Lint |
| `ruff check . --fix` | Lint and auto-fix |
| `ruff format .` | Format the code |
| `mypy .` | Static type checking |

CI runs lint, format check, type check and tests on every push and pull request to
`main` and `develop`.

---

## Git Flow

The team follows Git Flow. Two long-lived branches:

- **`main`** — production-ready code only. Never commit directly.
- **`develop`** — integration branch. All feature work merges here first.

Short-lived branches:

| Prefix | Purpose | Branch off | Merge into |
| --- | --- | --- | --- |
| `feature/*` | New functionality | `develop` | `develop` |
| `fix/*` | Bug fixes | `develop` | `develop` |
| `hotfix/*` | Urgent production fixes | `main` | `main` **and** `develop` |
| `release/*` | Release preparation | `develop` | `main` **and** `develop` |

### Typical workflow

```bash
git checkout develop
git pull origin develop

git checkout -b feature/equipment-catalog
# ... work, commit, work, commit ...
git push -u origin feature/equipment-catalog
# then open a Pull Request into develop
```

### Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add equipment list endpoint
fix: correct availability check on overlapping dates
docs: document the DATABASE_URL variable
test: cover the price calculation service
refactor: extract the booking number generator
chore: bump ruff to 0.16
```

Keep the history clean — one logical change per commit.

---

## Deployment (Render)

1. Push the repository to GitHub.
2. In Render, create a **New → Blueprint** and point it at this repository —
   [`render.yaml`](render.yaml) is picked up automatically.
3. The blueprint provisions a managed PostgreSQL instance and injects `DATABASE_URL`.
4. Set `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `CORS_ORIGINS` in the Render dashboard
   (`SECRET_KEY` is generated automatically).
5. Build runs `pip install -r requirements.txt`, `collectstatic` and `migrate`;
   the service starts with `gunicorn config.wsgi:application`.

---

## Team

| Name | Role | GitHub |
| --- | --- | --- |
| _TBD_ | Backend | [@username](https://github.com/username) |
| _TBD_ | Frontend | [@username](https://github.com/username) |
