# Welcome to Datlee!
Connect your data tools and get key business metrics via smart push notifications. **Stay on top of your business performance with ease.**

## One app to track all of your projects:
- Connect data sources
- Make data-driven decisions
- Get notified when things change

## Technical Specification
Monorepo with a Next.js frontend and a FastAPI backend for creating new projects, inviting collaborators by email, and connecting external data sources (Google Analytics and Stripe) to surface metrics. Includes a mobile app (external repository) with notification preferences that displays data from connected data sources via backend API.

- Frontend: [frontend/](frontend/README.md)
- Backend: [backend/](backend/main.py)
- Mobile (private): [mobile](https://github.com/a-bogomola/datlee-mobile) 

## Architecture

- Frontend
  - Next.js (App Router) 15, React 19, Tailwind CSS (via @tailwindcss/postcss)
  - Supabase authentication (client-side)
  - Project management UI (create, list, overview, team invites, data source connect)
- Backend
  - FastAPI with OAuth integrations for Google Analytics and Stripe
  - JWT-based auth middleware that validates incoming requests from the frontend
  - Notification preferences and scheduled tasks that connects with the mobile app
- Mobile
  - React Native (Expo), React Navigation, React Hooks, NativeWind for the frontend
  - Secure login via Supabase, JWT token stored via Expo SecureStore
  - Push notification frequency and types
  - Google Analytics & Stripe data fetched from the backend

High-level flow:
1. User authenticates (sign up + sign in) in the frontend via Supabase; the Supabase access token is attached as `Authorization: Bearer <token>` to backend requests.
2. Backend validates the token, extracts user id, and serves user-scoped resources.
3. Users create projects and invite collaborators. External sources can be connected for metrics.
4. To manage notifications and data display on the dashboard, users authenticate (only sign in) in the mobile app via Supabase.

## Architecture
### Frontend
- Entry/layout
  - Root layout and auth provider: [`RootLayout`](frontend/app/layout.js) wraps the app with [`AuthProvider`](frontend/contexts/AuthContext.js).
- Auth
  - Supabase client: [`supabase`](frontend/lib/supabaseClient.js)
  - Context: [`AuthProvider`](frontend/contexts/AuthContext.js)
- Profile pages (App Router)
  - Profile layout: [frontend/app/profile/layout.js](frontend/app/profile/layout.js)
  - Profile overview UI: [`ProfileOverview`](frontend/components/profile/overview/ProfileOverview.js)
- Projects UI
  - Create: [`NewProject`](frontend/components/profile/projects/NewProject.js) — inserts into `projects` and `project_to_user` via Supabase.
  - List: [`UserData`](frontend/components/profile/projects/ProjectsList.js)
  - Overview: [`ProjectOverview`](frontend/components/profile/projects/ProjectOverview.js) — project header, team invites, connect data sources, quick stats.
- Connectors UI
  - Google/Stripe connect panels live under [frontend/components/profile/connect](frontend/components/profile/connect)

Key dependencies: see [frontend/package.json](frontend/package.json)

#### Frontend environment

Create `frontend/.env.local`:
- NEXT_PUBLIC_SUPABASE_URL
- NEXT_PUBLIC_SUPABASE_ANON_KEY
- NEXT_PUBLIC_BACKEND_URL (e.g., http://localhost:8000)

#### Frontend commands

- Dev: `npm run dev`
- Build: `npm run build`
- Start: `npm start`

See [frontend/README.md](frontend/README.md) for Next.js details.

### Backend

- Application entry: [backend/main.py](backend/main.py)
  - CORS
  - Health route: `GET /`
  - Auth guard: [`get_current_user_id`](backend/main.py)
  - Project summary: [`get_summary`](backend/main.py) with request model [`ProjectRequest`](backend/main.py)
  - Projects list: `GET /api/projects` (user-scoped)
  - Notification preferences:
    - Read: [`get_notification_preferences`](backend/main.py) — `GET /api/notification-preferences`
    - Update: [`update_notification_preferences`](backend/main.py) — `PUT /api/notification-preferences` with model [`NotificationPreferences`](backend/main.py)
  - Google Analytics routes mounted under `/google` (see [backend/google_analytics](backend/google_analytics))
  - Stripe routes under `/stripe_data` (see [backend/stripe_data](backend/stripe_data))
- Auth helpers: [backend/auth.py](backend/auth.py)
- DB utilities: [backend/database.py](backend/database.py)
- Notifications
  - API/sender/scheduler: [backend/notifications](backend/notifications)
- Scheduled refresh
  - Jobs: [backend/scheduler/refresh.py](backend/scheduler/refresh.py)

Key dependencies: [backend/requirements.txt](backend/requirements.txt) (relaxed subset in [backend/requirements-relaxed.txt](backend/requirements-relaxed.txt))

#### Backend environment

Create `backend/.env`:
- SUPABASE_JWT_SECRET or verification settings matching your Supabase project
- FRONTEND_ORIGIN (for CORS in production)
- Google OAuth: GA_CLIENT_ID, GA_CLIENT_SECRET, GA_REDIRECT_URI
- Stripe OAuth: STRIPE_CLIENT_ID, STRIPE_CLIENT_SECRET, STRIPE_REDIRECT_URI
- Optional: STRIPE_WEBHOOK_SECRET, other provider secrets

#### Backend commands

- Install: `pip install -r backend/requirements.txt`
- Run dev: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`

### Data model (Supabase)

Tables used by the frontend:
- projects
  - project_name (text)
  - user_id (uuid)
  - created_at (timestamptz)
- project_to_user
  - project_id (uuid)
  - user_id (uuid)
  - role/status fields as needed

See creation and linking logic in:
- Create project flow: [`NewProject`](frontend/components/profile/projects/NewProject.js)

### API surface

Authorization: All protected endpoints expect `Authorization: Bearer <supabase_access_token>`.

- GET /
  - Health check.
- GET /api/projects
  - Returns projects for the authenticated user (see implementation in [backend/main.py](backend/main.py)).
- POST /api/summary
  - Body: [`ProjectRequest`](backend/main.py)
  - Returns a backend-generated summary for a project.
- GET /api/notification-preferences
  - Returns current user’s preferences: [`get_notification_preferences`](backend/main.py)
- PUT /api/notification-preferences
  - Body: [`NotificationPreferences`](backend/main.py)
  - Updates preferences: [`update_notification_preferences`](backend/main.py)
- Google Analytics under `/google`
  - OAuth connect and metrics: [backend/google_analytics/connect.py](backend/google_analytics/connect.py), [backend/google_analytics/fetch_metrics.py](backend/google_analytics/fetch_metrics.py)
- Stripe under `/stripe_data`
  - OAuth connect and metrics: [backend/stripe_data/connect.py](backend/stripe_data/connect.py), [backend/stripe_data/fetch_metrics.py](backend/stripe_data/fetch_metrics.py)

Auth middleware:
- [`get_current_user_id`](backend/main.py) resolves the Supabase user id from the incoming token

### Mobile app
- Frontend (React Native, Expo)
  - Navigation: Native Stack, screen transitions, persistent bottom Navbar (hidden on LogIn)
  - Auth: Supabase sign-in; access token stored in SecureStore and sent as Authorization: Bearer <token>
  - Dashboard: project selector, metric cards, percentage deltas, SVG background lines
  - Preferences:
    - Notification preferences (frequency + types)
    - Dashboard preferences (percentages, historical data, appearance)
    - Per-metric visibility toggles (traffic, bounce rate, session duration, conversion rate, revenue)

## Running locally

- Start backend:
  - `pip install -r backend/requirements.txt`
  - `uvicorn backend.main:app --reload --port 8000`
- Start frontend:
  - `npm install` in `frontend/`
  - `npm run dev`
- Set `NEXT_PUBLIC_BACKEND_URL` to the backend URL (http://localhost:8000).

## Project structure

- Frontend app tree: [frontend/app](frontend/app)
  - Global CSS: [frontend/app/globals.css](frontend/app/globals.css)
  - Layout: [frontend/app/layout.js](frontend/app/layout.js)
  - Profile routes: [frontend/app/profile](frontend/app/profile)
- Frontend components: [frontend/components](frontend/components)
  - Auth: [frontend/components/auth](frontend/components/auth)
  - Profile overview: [`ProfileOverview`](frontend/components/profile/overview/ProfileOverview.js)
  - Projects:
    - Create: [`NewProject`](frontend/components/profile/projects/NewProject.js)
    - List: [`UserData`](frontend/components/profile/projects/ProjectsList.js)
    - Overview: [`ProjectOverview`](frontend/components/profile/projects/ProjectOverview.js)
- Backend services:
  - API entry: [backend/main.py](backend/main.py)
  - Auth: [backend/auth.py](backend/auth.py)
  - Providers: [backend/google_analytics](backend/google_analytics), [backend/stripe_data](backend/stripe_data)
  - Notifications: [backend/notifications](backend/notifications)
  - Scheduler: [backend/scheduler](backend/scheduler)
 
## Our Team
Aleksandra Bogomola [a-bogomola](https://github.com/a-bogomola), Valerija Kovalova [kyeenno](https://github.com/kyeenno), Valters V., Renars Niedra
