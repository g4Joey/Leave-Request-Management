# Frontend (Create React App)

Dev server: `npm start` (default http://localhost:3000)
Build: `npm run build`

## Setup

1. Install Node.js (>=18) and npm.
2. From `frontend/` run:

```bash
npm install
npm start
```

## Backend API configuration

Create `.env` (or copy `.env.example`) and ensure:

```bash
REACT_APP_API_BASE=http://127.0.0.1:8000
```

The app will call `http://127.0.0.1:8000/api/...` directly.

## Auth flow

Login posts to `/api/auth/token/` with body `{ username: email, password }`.
Tokens stored in `localStorage` keys: `access`, `refresh`.
Dashboard fetches `/api/users/me/` to display profile details.
