# job-platform-backend

## Requirements

- Python 3.14
- Django 6.0, DRF
- PostgreSQL

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

SECRET_KEY can be generated from https://djecrety.ir/

### 3. Build and run container

```bash
docker compose up --build
```

### 4. Create a superuser for admin panel (if needed)

```bash
docker compose exec django python manage.py createsuperuser
```

## Running natively

### 1. Clone the repository and install PostgreSQL

```bash
git clone <repo-url>
cd job-platform-backend
```

Also install PostgreSQL from https://www.postgresql.org/download/ and create the database:
```sql
CREATE ROLE DB_USER WITH LOGIN SUPERUSER CREATEDB CREATEROLE PASSWORD 'DB_PASSWORD';
CREATE DATABASE DB_NAME OWNER DB_USER;
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

SECRET_KEY can be generated from https://djecrety.ir/

### 5. Create a superuser for admin panel (if needed)

```bash
python manage.py createsuperuser
```

### 6. Run migrations (if needed)

```bash
python manage.py migrate
```

### 7. Run the development server

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
| `SECRET_KEY` | Django secret key (https://djecrety.ir/) |
| `DEBUG` | Debug mode (True for development) |
| `DB_NAME` | Database name (Default: jobplatform) |
| `DB_USER` | Database username (Default: jobplatform) |
| `DB_PASSWORD` | Database platform (Default: jobplatform) |
| `DB_HOST` | Database host (Default: localhost) |
| `DB_PORT` | Database port (Default: 5432) |

## Progress

- Implemented most of use cases 1 and 2
- Missing: CV upload, Profile score calculation (We need to decide where calculation should happen)
