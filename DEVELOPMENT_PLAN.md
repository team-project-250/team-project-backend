# Development Plan

Step-by-step plan for the Team Project, as required by the *Technical Start: Roadmap for Developers* checklist.
This document covers **both** repositories — [`team-project-backend`](https://github.com/glor1ee/team-project-backend) and [`team-project-frontend`](https://github.com/glor1ee/team-project-frontend).

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

- [ ] Project skeleton: `config/` with `settings/` split by environment (base / development / production)
- [ ] Connect PostgreSQL via `django-environ` (`DATABASE_URL`), run the initial `migrate`
- [ ] Wire up DRF, django-filter, CORS and drf-spectacular; root URLs (`/admin/`, `/api/`, schema)
- [ ] Create the `apps/catalog` and `apps/bookings` applications
- [ ] Define the core domain models (catalog first, then bookings) + migrations
- [ ] Register everything in the Django admin and add a catalog seed fixture
- [ ] Add a service layer (`apps/*/services.py`) between views and models
- [ ] Structured logging and a DRF exception handler

**Frontend**

- [ ] Set up routing (React Router)
- [ ] Application layout: header, navigation, content area, footer
- [ ] Global state approach agreed (Context / Zustand / Redux Toolkit)
- [ ] Base API client with typed responses and error handling

**Definition of done:** the frontend renders a real layout and fetches real data from a database-backed endpoint.

---

## Stage 2 — Authentication

- [ ] Backend: staff auth via the Django admin (customers are identified by phone, no account)
- [ ] Backend: decide if any public endpoint needs auth; if so, add DRF token/JWT auth
- [ ] Backend: DRF permission classes on protected endpoints + tests
- [ ] Frontend: registration and login pages with form validation
- [ ] Frontend: token storage, auth context, automatic refresh
- [ ] Frontend: protected routes and a redirect for unauthenticated users

**Definition of done:** a user can register, log in, stay logged in after a page reload, and log out.

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
- [ ] Equipment catalog — list with filters (category, city, price, availability), search, sorting, pagination
- [ ] Equipment detail — full specs, gallery, "what's included", use-case tags
- [ ] Availability calendar — booked dates per equipment for a given month
- [ ] Booking flow — create a rental with server-side availability check and price calculation
- [ ] My bookings — look up bookings by phone number, cancel a booking

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
