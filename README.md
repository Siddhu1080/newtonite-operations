# Newtonite Operations

Newtonite Operations is an internal operations management application built to manage teams, work items, comments, and activity history. It focuses on team-based access control, reliable work-item creation, and handling concurrent updates.

## Features

- **Authentication:** User registration and login using JWT authentication.
- **Team Management:** Create teams, manage membership, and assign admin or member roles.
- **Work Item Management:** Create, view, filter, paginate, and update work items.
- **Team-Based Authorization:** Users can access work items and related information only when they belong to the relevant team.
- **Optimistic Concurrency Control:** Version-based updates help prevent stale changes from overwriting newer data.
- **Idempotent Creation:** Repeated requests with the same idempotency key and payload return the original work item.
- **Comments:** Team members can add and view comments.
- **Activity History:** Records work-item changes for traceability.
- **Automated Tests:** Tests cover authentication, authorization, validation, duplicate requests, and concurrent-update conflicts.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | MySQL |
| ORM | SQLAlchemy |
| Authentication | JWT |
| Password Hashing | pwdlib |
| Frontend | React and Vite |
| Testing | pytest |

## Project Structure

```text
Newtonite-operations/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend//
├── ENGINEERING_DECISIONS.md
└── README.md
```


## Prerequisites

- Python 3.10 or later
- MySQL
- Node.js and npm, if running the React frontend
- Git

## Backend Setup

### 1. Clone the repository

```bash
git clone https://github.com/Siddhu1080/newtonite-operations.git
cd newtonite-operations
```

Replace the placeholder with your actual repository URL.

### 2. Create and activate a virtual environment

From the project root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the `backend` directory and configure the database connection and JWT secret using the environment variable names expected by the application.

Example:

```env
DATABASE_URL=mysql+pymysql://<username>:<password>@localhost/<database_name>
SECRET_KEY=<your_secure_random_secret>
```

Replace the placeholders with your own values. Do not commit `.env` or expose real credentials in the repository.

Create the MySQL database and ensure the database URL matches your configuration. Apply the project's database initialization or migration procedure before starting the application.

### 5. Start the backend

From the `backend` directory, run:

```powershell
python -m uvicorn app.main:app --reload
```

The API will normally be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## Frontend Setup
```
Open a second terminal from the project root:

cd frontend
npm install
npm run dev

Use the local URL printed by Vite. Ensure the frontend's API URL and the backend's CORS configuration match your local setup.
```

Use the local URL printed by Vite. Ensure the frontend's API URL and the backend's CORS configuration match your local setup.

## Running Tests

The backend uses `pytest` for automated testing. Tests require a separate test database configured through the `TEST_DATABASE_URL` environment variable.

**Important:** Never use the production database for testing. Use a separate MySQL test database.

From the `backend` directory, configure `TEST_DATABASE_URL` with your test database connection string.

**Windows PowerShell:**

```powershell
$env:TEST_DATABASE_URL = "mysql+pymysql://<username>:<password>@localhost/<test_database>"
$env:PYTHONPATH = "."
python -m pytest -v
```

**Ubuntu/Linux:**

```bash
export TEST_DATABASE_URL="mysql+pymysql://<username>:<password>@localhost/<test_database>"
export PYTHONPATH="."
python -m pytest -v
```

Replace the placeholders with your test database credentials. Check the test output for the actual number of passed and failed tests.

## Engineering Decisions

Important design choices, including team-based authorization, optimistic concurrency control, idempotent work-item creation, activity history, and automated testing, are documented in [`ENGINEERING_DECISIONS.md`](ENGINEERING_DECISIONS.md).

## Known Limitations

- JWT access tokens expire after a limited period; refresh-token support is not implemented.
- Notifications and background processing are not implemented.
- Automated tests do not replace full production security, load, and integration testing.
- Production deployment configuration, monitoring, and operational hardening may require additional work.

## Security Notes

- Keep database credentials and JWT secrets out of source control.
- Use a strong, randomly generated JWT secret.
- Use HTTPS and appropriate production configuration when deploying the application.

## License

No license has been specified for this project.
