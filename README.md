# job-platform-backend

![Job Bless Logo](images/logo-with-background-and-text.png)

The backend server for JobBless, a job seeking platform built in 2026 for the Software Engineering course at CEID, University of Patras.

## Team Members
- **ΑΔΑΜΟΠΟΥΛΟΣ ΘΕΟΔΩΡΟΣ / vortex3964** - ΑΜ:1108389 - 6ο εξαμηνο
- **ΑΛΕΞΑΝΔΡΟΠΟΥΛΟΣ ΘΕΟΔΩΡΟΣ / teettt1** - ΑΜ: 1108347 - 6ο εξαμηνο
- **ΔΗΜΟΠΟΥΛΟΣ ΗΛΙΑΣ / LinkBoi00** - ΑΜ:1108376 - 6ο εξαμηνο
- **ΧΑΪΔΟΓΙΑΝΝΟΣ ΜΑΡΙΟΣ-ΔΗΜΗΤΡΙΟΣ / Dimitris34** - ΑΜ:1112101 - 6ο εξαμηνο
- **ΧΑΤΖΗΔΗΜΗΤΡΙΟΥ ΣΤΥΛΙΑΝΟΣ / Stelios-Chatzid** - ΑΜ:1112144 - 6ο εξαμηνο

## Technologies

- Docker
- Python 3.14
- Django 6.0, DRF
- PostgreSQL
- MinIO
- LiveKit
- Redis
- Celery
- Groq API

## Running with Docker (recommended)

### 1. Clone the repository

```bash
git clone <repo-url>
cd job-platform-backend
```

### 2. Set up environment variables

Copy `.env.example` to `.env` and fill in the values according to the table below:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key, generate one at https://djecrety.ir/ | - |
| `DEBUG` | Enable debug mode | `True` |
| `DB_NAME` | Database name | `jobplatform` |
| `DB_USER` | Database user | `jobplatform` |
| `DB_PASSWORD` | Database password | `jobplatform` |
| `MINIO_USER` | MinIO root user | `jobplatform` |
| `MINIO_PASSWORD` | MinIO root password | `jobplatform` |
| `MINIO_BUCKET` | MinIO bucket name | `jobplatform` |
| `HOST_PUBLIC_ENDPOINT` | Your machine's public IP for MinIO and LiveKit (run `ipconfig` on Windows or `ifconfig` on Linux/Mac) | `localhost` |
| `LIVEKIT_API_KEY` | LiveKit API key, any string you choose | - |
| `LIVEKIT_API_SECRET` | LiveKit API secret, any string you choose (minimum 32 characters) | - |
| `AI_BACKEND` | AI provider to use, either `groq` or `local` | `groq` |
| `AI_GROQ_MODEL` | Groq model name (only when `AI_BACKEND=groq`) | `meta-llama/llama-4-scout-17b-16e-instruct` |
| `GROQ_API_KEY` | Groq API key (only when `AI_BACKEND=groq`) | - |
| `AI_GPU_VENDOR` | GPU vendor for local inference: `nvidia`, `amd`, or `cpu` (only when `AI_BACKEND=local`) | `cpu` |
| `AI_LOCAL_MODEL` | Local model name (only when `AI_BACKEND=local`) | `qwen2.5-3b-instruct-q4_k_m.gguf` |

### 3. Build and run container

```bash
docker compose up --build
```

### 4. Create a superuser for admin panel (if needed)

```bash
docker compose exec django python manage.py createsuperuser
```

## API Endpoints

### Auth
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/login/` | Login and get token | No |
| POST | `/api/auth/logout/` | Invalidate session token | Token |

### Users
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/users/` | Search users by username, first name or last name (`?search=query`) | Token |
| GET | `/api/users/me/` | Get current user info including avatar | Token |
| PATCH | `/api/users/me/` | Update avatar, first name, last name, email | Token |
| GET | `/api/users/<id>/` | Get public user info for a specific user | Token |

### Candidates
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/candidates/<id>/` | Get candidate profile | Token |
| GET | `/api/candidates/me/` | Get current user's candidate profile | Token |
| PUT/PATCH | `/api/candidates/me/` | Update current user's candidate profile | Token |
| GET | `/api/candidates/background/skills/` | List candidate's skills (use `?candidate_id=` to view another candidate's) | Token |
| POST | `/api/candidates/background/skills/` | Add a skill | Token |
| PUT/PATCH | `/api/candidates/background/skills/<id>/` | Update a skill | Token |
| DELETE | `/api/candidates/background/skills/<id>/` | Delete a skill | Token |
| GET | `/api/candidates/background/education/` | List candidate's education entries (use `?candidate_id=` to view another candidate's) | Token |
| POST | `/api/candidates/background/education/` | Add an education entry | Token |
| PUT/PATCH | `/api/candidates/background/education/<id>/` | Update an education entry | Token |
| DELETE | `/api/candidates/background/education/<id>/` | Delete an education entry | Token |
| GET | `/api/candidates/background/experience/` | List candidate's work experiences (use `?candidate_id=` to view another candidate's) | Token |
| POST | `/api/candidates/background/experience/` | Add a work experience | Token |
| PUT/PATCH | `/api/candidates/background/experience/<id>/` | Update a work experience | Token |
| DELETE | `/api/candidates/background/experience/<id>/` | Delete a work experience | Token |

### Employers
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/employers/` | List all employer profiles | Token |
| GET | `/api/employers/<id>/` | Get employer profile | Token |
| GET | `/api/employers/me/` | Get current user's employer profile | Token |
| PUT/PATCH | `/api/employers/me/` | Update current user's  employer profile | Token |

### Jobs
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/jobs/` | List all active job postings (employer sees inactive ones too) | Token |
| POST | `/api/jobs/` | Create a job posting (employer only) | Token |
| GET | `/api/jobs/<id>/` | Get job posting details | Token |
| PUT/PATCH | `/api/jobs/<id>/` | Update a job posting (employer only) | Token |
| DELETE | `/api/jobs/<id>/` | Delete a job posting (employer only) | Token |
| POST | `/api/jobs/<id>/apply/` | Apply for a job (candidate only) | Token |
| GET | `/api/jobs/applications/` | List applications (employer: all for their postings, candidate: own applications) | Token |
| PATCH | `/api/jobs/applications/<id>/status/` | Accept/reject an application (employer only) | Token

### Reviews
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/reviews/<employer_id>/` | List all reviews for an employer | Token |
| POST | `/api/reviews/<employer_id>/` | Leave a review for an employer | Token |
| GET | `/api/reviews/<employer_id>/<id>/` | Get a single review | Token |
| PUT/PATCH | `/api/reviews/<employer_id>/<id>/` | Edit a review (owner only) | Token |
| DELETE | `/api/reviews/<employer_id>/<id>/` | Delete a review (owner only) | Token |

### Social
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/posts/` | List all posts | Token |
| POST | `/api/posts/` | Create a post | Token |
| GET | `/api/posts/<id>/` | Get post details | Token |
| PUT/PATCH | `/api/posts/<id>/` | Update a post | Token |
| DELETE | `/api/posts/<id>/` | Delete a post | Token |
| GET | `/api/posts/<id>/comments/` | List comments on a post | Token |
| POST | `/api/posts/<id>/comments/` | Add a comment to a post | Token |
| GET | `/api/posts/<id>/comments/<comment_id>/` | Get a specific comment | Token |
| PUT/PATCH | `/api/posts/<id>/comments/<comment_id>/` | Update a comment | Token |
| DELETE | `/api/posts/<id>/comments/<comment_id>/` | Delete a comment | Token |
| POST | `/api/posts/<id>/like/` | Like and Unlike a post | Token |
| GET | `/api/posts/<id>/images/` | List all images for a post | Token |
| POST | `/api/posts/<id>/images/` | Upload an image to a post | Token |
| GET | `/api/posts/<id>/images/<image_id>/` | Get a specific image | Token |
| PATCH | `/api/posts/<id>/images/<image_id>/` | Replace an image | Token |
| DELETE | `/api/posts/<id>/images/<image_id>/` | Delete an image | Token |

### Messaging
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/conversations/` | List all conversations | Token |
| POST | `/api/conversations/` | Start or retrieve a conversation | Token |
| DELETE | `/api/conversations/<id>/` | Delete a conversation and all its messages | Token |
| GET | `/api/conversations/<id>/messages/` | List all messages in a conversation | Token |
| DELETE | `/api/conversations/<id>/messages/<message_id>/` | Delete a message (sender only) | Token |
| WS | `ws/conversations/<id>/?token=<token>` | Connect to live conversation | Token |

### Stats
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/stats/salary-range-distribution/` | Salary bracket distribution with dynamic bucket sizing (supports filtering by title) | Token |
| GET | `/api/stats/jobs-by-title/` | List job postings grouped by title | Token |
| GET | `/api/stats/candidates-by-education/` | Candidate counts grouped by education level (supports filtering by title) | Token |
| GET | `/api/stats/top-skills/` | Top 10 most in-demand skills (supports filtering by title) | Token |
| GET | `/api/stats/top-companies/` | Top 10 companies by number of job postings (supports filtering by title) | Token |
| GET | `/api/stats/avg-salary-by-title/` | Average min/max salary ranges grouped by job title | Token |
| GET | `/api/stats/jobs-over-time/` | Daily job posting counts over time (supports filtering by title) | Token |
| GET | `/api/stats/remote-vs-onsite/` | Distribution of remote vs on-site positions (supports filtering by title) | Token |
| GET | `/api/stats/jobs-by-contract-type/` | Job counts grouped by contract type (supports filtering by title) | Token |
| GET | `/api/stats/avg-salary-by-contract-type/` | Average min/max salary ranges grouped by contract type (supports filtering by title) | Token |
| GET | `/api/stats/most-competitive-jobs/` | Top 10 jobs ranked by application count | Token |

### Mock AI Interviews
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/sessions/` | List all user's interview sessions | Token |
| POST | `/api/sessions/` | Create a new interview session (requires `job_posting_id`) | Token |
| GET | `/api/sessions/<id>/` | Get session details and full message history | Token |
| PATCH | `/api/sessions/<id>/` | Update session (e.g. title) | Token |
| DELETE | `/api/sessions/<id>/` | Delete a session | Token |
| GET | `/api/sessions/<id>/messages/` | List all messages in a session | Token |
| WS | `ws/interview/<id>/?token=<token>` | Connect to live interview session | Token |

### Calls (LiveKit)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/calls/` | List all rooms where you are host or participant (excludes expired) | Token |
| POST | `/api/calls/` | Create a room (employer only) | Token |
| GET | `/api/calls/<id>/` | Get room details | Token |
| PUT/PATCH | `/api/calls/<id>/` | Update room (host only) | Token |
| DELETE | `/api/calls/<id>/` | Delete room (host only) | Token |
| POST | `/api/calls/<id>/token/` | Get LiveKit join token (must be participant, meeting must have started and not expired) | Token |
| POST | `/api/calls/<id>/participants/` | Add a user to the room by `user_id` (host only) | Token |
| DELETE | `/api/calls/<id>/participants/` | Remove yourself from the room | Token |


## Token-based authentication

All protected APIs require a token in the request header:

```
Authorization: Token <your-token>
```
