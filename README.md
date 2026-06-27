# 5stack.gg

V-Match is a Valorant matchmaking MVP for connecting players based on rank, mood, and agent priority. It supports Google sign-in, user profile setup, party creation, party search, join requests, invites, and live party management.

## Tech Stack

- Frontend: Vue 3, TypeScript, Pinia, vanilla CSS, Vite
- Authentication: Firebase Google Sign-In
- Backend: FastAPI
- Database: PostgreSQL
- Runtime: Node.js, Python, WSL Ubuntu

## Features

- Google sign-in through Firebase
- Username setup in the format `username#tagline`
- Edit profile username and logout from the navbar
- Save playstyle preferences:
  - Rank
  - Mood
  - Draggable agent priority
- Create a party with a required party code
- Search for existing parties
- Send and receive join requests and party invites
- Accept or reject incoming requests
- View active party members and party code
- Leave, disband, or remove members from a party
- Filter individual players by mood and rating range
- Show player rank, mood, username, and top 5 priority agents in cards

## Project Structure

```text
proj2/
├── backend/
│   ├── main.py
│   ├── routes.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── database.py
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── stores/
│   │   └── assets/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Setup

### Backend

1. Open a terminal in `backend`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Ensure PostgreSQL is running.
4. Make sure `backend/.env` contains your database URL.
5. Start the backend:

```bash
uvicorn main:app --reload
```

### Frontend

1. Open a terminal in `frontend`.
2. Install dependencies if needed:

```bash
npm install
```

3. Start the frontend:

```bash
npm run dev
```

## Database Notes

The backend reads the connection string from `backend/.env` using `DATABASE_URL`.

Example:

```env
DATABASE_URL=postgresql+asyncpg://myuser:mypassword@localhost:5432/partyfinder
```

## Useful Commands

From the project notes:

### Backend

```bash
sudo service postgresql start
sudo service postgresql status
sudo -u postgres psql
\c partyfinder
GRANT ALL ON SCHEMA public TO myuser;
GRANT ALL PRIVILEGES ON DATABASE partyfinder TO myuser;
source venv/bin/activate
uvicorn main:app --reload
```

### Frontend

```bash
npm run dev
```

## MVP Flow

1. User signs in with Google.
2. User sets `username#tagline`.
3. User saves rank, mood, and agent priority.
4. User chooses to create a party or search for one.
5. Users can send/receive join requests and invites.
6. Parties can be managed by leaders and members can leave voluntarily.

## Notes

- The app is designed as a small MVP and favors low-cost/free-tier tooling.
- Some values and rules were tuned to keep the UI simple and readable for early testing.
