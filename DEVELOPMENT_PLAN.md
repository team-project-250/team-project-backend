# Development Plan

Step-by-step plan for the Team Project, as required by the *Technical Start: Roadmap for Developers* checklist.
This document covers **both** repositories — [`team-project-backend`](https://github.com/team-project-250/team-project-backend) and [`team-project-frontend`](https://github.com/team-project-250/team-project-frontend).

---

## Stage 0 — Technical start ✅ (done)

- [x] Development environment set up for client and server
- [x] Multi-repo configured — separate frontend and backend repositories
- [x] GitHub repositories created and connected
- [x] Git Flow agreed: `main` / `develop` / `feature/*` / `fix/*`
- [x] Empty backend project initialised (Django + DRF — migrated from the initial FastAPI scaffold)
- [x] Empty frontend project initialised (React + Vite + TypeScript)
- [x] All required dependencies installed
- [x] TypeScript, ESLint, Prettier, Ruff, mypy configured
- [x] Sanity check: frontend page renders `Hello world!`
- [x] Sanity check: backend endpoint returns `Hello world!` and answers a real request
- [x] UI library chosen
- [x] CI pipelines running on every push and pull request
- [x] README files written for both repositories

---

## Stage 1 — Foundation

**Backend**

- [x] Project skeleton: `config/` with `settings/` split by environment (base / development / production)
- [x] Connect PostgreSQL via `django-environ` (`DATABASE_URL`), run the initial `migrate`
- [x] Wire up DRF, django-filter, CORS and drf-spectacular; root URLs (`/admin/`, `/api/`, schema)
- [x] Create the `apps/catalog` and `apps/bookings` applications
- [x] Define the core domain models (catalog first, then bookings) + migrations
- [x] Register everything in the Django admin and add a catalog seed fixture
- [x] Add a service layer (`apps/*/services.py`) between views and models
- [x] Structured logging and a DRF exception handler
- [x] Rate limiting across the public API (lookup, cancel, callback-request and booking creation are throttled; `bookings/quote/` is read-only with no side effects, deliberately left unthrottled)

**Frontend**

- [x] Set up routing (React Router)
- [x] Application layout: header, navigation, content area, footer
- [x] Global state approach agreed (React Context)
- [ ] Base API client with typed responses and error handling (`src/api/client.ts` exists, not used by the pages yet)

**Definition of done:** the frontend renders a real layout and fetches real data from a database-backed endpoint.

---

## Stage 2 — Authentication ✅ (decided: no customer accounts)

Renting doesn't need an account: a customer books with a name, phone and e-mail,
and later finds or cancels the booking by phone + booking number. So there is no
customer registration/login, and the frontend needs no auth pages.

- [x] Backend: staff auth via the Django admin
- [x] Backend: public endpoints stay anonymous; the phone-based ones are rate-limited instead
- [x] Frontend: no login/registration needed

---

## Stage 3 — Core features

Work through the features **one by one, commit by commit**. For every feature:

1. Create `feature/<name>` off `develop`
2. Backend: model → migration → serializer → view → URL → tests
3. Frontend: API call → component → page → states (loading / empty / error)
4. Open a Pull Request into `develop`, get a review, merge

Feature backlog (equipment-rental service) — see [`docs/BACKEND_ROADMAP.md`](docs/BACKEND_ROADMAP.md) for the milestone breakdown:

- [x] Cities & pickup points — `GET /api/cities/` for the header/footer city selector
- [x] Customer reviews — moderated `GET /api/reviews/`
- [x] Equipment catalog — list with filters (category, city, price), search, sorting, pagination (availability filter comes in M8)
- [x] Equipment detail — full specs, gallery, "what's included", benefits
- [x] Availability calendar — booked dates per equipment for a given month
- [x] Booking flow — create a rental with server-side availability check and price calculation
- [x] One-click booking — record a phone number (+ optional equipment/dates) for a manager callback
- [x] My bookings — look up bookings by phone number, cancel a booking
- [x] Editable home-page content — hero, about, rental steps/terms, site settings, all managed in the admin
- [x] Home aggregator — `GET /api/home/` for a single landing-page fetch
- [x] Card page backend — badges, per-product "suitable for", breadcrumbs, related equipment, delivery/payment content, hardened quick-booking (phone format, date conflict, duplicates)

---

## Stage 3b — Connect the frontend to the API ⏳ (next)

The site is a finished UI but still reads everything from `src/data/*.ts` mock
files and keeps bookings in browser memory. Each screen switches to the API in its
own PR:

- [ ] API client + types generated from / matching the OpenAPI schema (`/api/schema/`)
- [ ] Cities and pickup points → `GET /api/cities/`
- [ ] Catalog and filters → `GET /api/categories/`, `GET /api/equipment/`
- [ ] Product page → `GET /api/equipment/{slug}/`, `/related/`, `/availability/`
- [ ] Booking form → `POST /api/bookings/quote/` and `POST /api/bookings/` (handle 400 / 409)
- [ ] "1-click" booking → `POST /api/callback-requests/`
- [ ] Home page content and reviews → `GET /api/home/`
- [ ] "My bookings" page → `GET /api/bookings/?phone=`, `POST /api/bookings/{number}/cancel/`
- [ ] Remove the mock data files and the old `/api/hello` sanity call

**Definition of done:** the site shows what the admin panel contains, and a booking
made on the site appears in the admin.

---

## Stage 4 — Polish

- [ ] Responsive layout (mobile / tablet / desktop)
- [ ] Loading skeletons and empty states everywhere
- [ ] Consistent error messages and toasts
- [ ] Accessibility pass: keyboard navigation, labels, contrast
- [ ] Pagination / filtering / sorting where lists are long
- [ ] Performance: query optimisation on the backend, code splitting on the frontend

---

## Stage 5 — Testing and finalisation

- [ ] Backend: unit + integration tests (pytest-django + DRF `APIClient`), meaningful coverage on business logic
- [ ] Frontend: component tests (Vitest + Testing Library)
- [ ] Manual end-to-end pass through every user flow
- [ ] Cross-browser check (Chrome, Firefox, Safari)
- [ ] READMEs finalised with screenshots and the live demo links
- [ ] `.env.example` files match what the code actually reads

---

## Stage 6 — Deploy

- [ ] Backend deployed to [Render](https://render.com) via `render.yaml` (Gunicorn, `python manage.py migrate` on release)
- [ ] Managed PostgreSQL instance provisioned and migrations applied
- [ ] S3-compatible media bucket configured (`AWS_STORAGE_BUCKET_NAME` etc.) and `NUM_PROXIES` set for Render's proxy chain
- [ ] Frontend deployed to [Vercel](https://vercel.com)
- [ ] `VITE_API_URL` on the frontend points at the deployed backend
- [ ] `CORS_ORIGINS` on the backend points at the deployed frontend
- [ ] Live links added to both READMEs
- [ ] `develop` merged into `main` and tagged `v1.0.0`

---

## Working agreements

- Never push directly to `main` or `develop` — always through a Pull Request
- Every PR needs at least one review from a teammate
- CI must be green before merging
- Keep the commit history clean: one logical change per commit, Conventional Commits style
- Pull `develop` before starting a new branch to avoid merge conflicts
- If a task takes longer than a day, split it into smaller ones
