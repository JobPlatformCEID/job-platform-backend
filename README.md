# job-platform-backend

## Requirements

- Python 3.14
- Django 6.0, DRF
- PostgreSQL (Planned, using SQLite for now)

## Running with Docker (recommended)

### 1. Clone the repository

```bash
git clone <repo-url>
cd job-platform-backend
```

### 2. Set up environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### 3. Create a superuser

```bash
python manage.py createsuperuser
```

### 4. Build and run container

```bash
docker compose up --build
```

## Running natively

### 1. Clone the repository

```bash
git clone <repo-url>
cd job-platform-backend
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### 5. Create a superuser

```bash
python manage.py createsuperuser
```

### 6. Run the development server

```bash
python manage.py runserver
```

## API Endpoints

### Auth
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/login/` | Login and get token | No |

### Candidates
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/candidates/me/` | Get candidate profile | Token |
| PUT | `/api/candidates/me/` | Update candidate profile | Token |

### Employers
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/employers/me/` | Get employer profile | Token |
| PUT | `/api/employers/me/` | Update employer profile | Token |

### Jobs
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/jobs/` | List all active job postings | Token |
| POST | `/api/jobs/` | Create a job posting (employer only) | Token |
| GET | `/api/jobs/<id>/` | Get job posting details | Token |
| PUT | `/api/jobs/<id>/` | Update a job posting (employer only) | Token |
| DELETE | `/api/jobs/<id>/` | Delete a job posting (employer only) | Token |
| POST | `/api/jobs/<id>/apply/` | Apply for a job (candidate only) | Token |
| GET | `/api/jobs/applications/` | List applications (employer only) | Token |

APIs were tested with Postman.

## Token-based authentication (temporary)

All protected APIs require a token in the request header:

```
Authorization: Token <your-token>
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | Debug mode (True/False) |

## Progress

- Implemented most of use cases 1 and 2
- Missing: CV upload, Profile score calculation (We need to decide where calculation should happen)
