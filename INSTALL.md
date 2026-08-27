# Velora Installation Guide

This guide walks you through setting up Velora on a new computer for local development and testing.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
- **Git**: To clone the repository.
- **Python 3.11+**: For the Django backend.
- **Node.js (v18+) & npm**: For the React frontend.

---

## 1. Clone the Repository

First, clone the project to your local machine and navigate into the project folder:

```bash
git clone <your-repository-url>
cd Velora
```

---

## 2. Backend Setup (Django)

Velora's backend is powered by Django and uses SQLite by default for local development.

### Create a Virtual Environment

It is highly recommended to use a virtual environment to manage Python dependencies.

**On Windows:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install Dependencies

With the virtual environment activated, install the required packages:

```bash
pip install -r backend/requirements/local.txt
```

### Configure Environment Variables

The system relies on environment variables for configuration (like AI keys and database settings).

1. Copy the example environment file:
   **On Windows:** `copy .env.example .env`
   **On macOS/Linux:** `cp .env.example .env`
2. Open the newly created `.env` file and fill in any necessary values. The `.env` file will automatically load when you start the server.

### Run Migrations & Seed Data

Navigate to the backend directory, initialize the database, and load the demo data:

```bash
cd backend
python manage.py migrate
```

To create sample data (patients, doctors, etc.) for testing:
```bash
python manage.py seed_demo
```
*(The demo credentials created will be `admin@velora.com`, `doctor@velora.com`, etc. all with password `password123`)*

### Start the Backend Server

```bash
python manage.py runserver
```
*The backend API will now be running at `http://127.0.0.1:8000`.*

---

## 3. Frontend Setup (React)

Open a **new terminal window**, navigate to the project root, and then into the frontend directory.

### Install Dependencies

```bash
cd frontend
npm install
```

### Start the Frontend Server

```bash
npm run dev
```

*The frontend application will start and is accessible at `http://localhost:5173`.* 
*(API requests are automatically proxied to the backend via Vite).*

---

## 4. Optional Configurations

### Clinical Assistant (AI)
To enable the free conversational assistant, update your `.env` file with a free Groq or Gemini key:
```env
AI_PROVIDER=groq
AI_API_KEY=your-groq-api-key
```

### Background Workers
If you need to test active prescription monitoring or background jobs, open another terminal and run:
```bash
cd backend
../.venv/Scripts/python manage.py process_medication_due --watch --interval 30
```
*(Use `../.venv/bin/python` on Mac/Linux).*

---

## Troubleshooting

- **"unable to open database file"**: Ensure you are running `python manage.py` from *inside* the `backend/` directory, and that your `.env` file does not contain a broken `SQLITE_PATH` relative path.
- **Python not recognized**: On Windows, ensure Python is added to your system PATH.
- **Port already in use**: If port 8000 or 5173 is occupied, ensure no other applications (like another project) are currently running on those ports.
