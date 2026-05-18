# job-platform-backend

the backend made for the software engineering course for CEID 2026.

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
| PUT | `/api/candidates/me/` | Update current user's candidate profile | Token |
| GET | /api/candidates/background/skills/ | List candidate's skills | Token |
| POST | /api/candidates/background/skills/ | Add a skill | Token |
| PUT | /api/candidates/background/skills/<id>/ | Update a skill | Token |
| DELETE | /api/candidates/background/skills/<id>/ | Delete a skill | Token |
| GET | /api/candidates/background/education/ | List candidate's education entries | Token |
| POST | /api/candidates/background/education/ | Add an education entry | Token |
| PUT | /api/candidates/background/education/<id>/ | Update an education entry | Token |
| DELETE | /api/candidates/background/education/<id>/ | Delete an education entry | Token |
| GET | /api/candidates/background/experience/ | List candidate's work experiences | Token |
| POST | /api/candidates/background/experience/ | Add a work experience | Token |
| PUT | /api/candidates/background/experience/<id>/ | Update a work experience | Token |
| DELETE | /api/candidates/background/experience/<id>/ | Delete a work experience | Token |

### Employers
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/employers/` | List all employer profiles | Token |
| GET | `/api/employers/<id>` | Get employer profile | Token |
| GET | `/api/employers/me/` | Get current user's employer profile | Token |
| PUT | `/api/employers/me/` | Update current user's  employer profile | Token |

### Jobs
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/jobs/` | List all active job postings | Token |
| POST | `/api/jobs/` | Create a job posting (employer only) | Token |
| GET | `/api/jobs/<id>/` | Get job posting details | Token |
| PUT | `/api/jobs/<id>/` | Update a job posting (employer only) | Token |
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
| PUT | `/api/reviews/<employer_id>/<id>/` | Edit a review (owner only) | Token |
| DELETE | `/api/reviews/<employer_id>/<id>/` | Delete a review (owner only) | Token |

### Social
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/posts/` | List all posts | Token |
| POST | `/api/posts/` | Create a post | Token |
| GET | `/api/posts/<id>/` | Get post details | Token |
| PATCH | `/api/posts/<id>/` | Update a post | Token |
| DELETE | `/api/posts/<id>/` | Delete a post | Token |
| GET | `/api/posts/<id>/comments/` | List comments on a post | Token |
| POST | `/api/posts/<id>/comments/` | Add a comment to a post | Token |
| GET | `/api/posts/<id>/comments/<comment_id>/` | Get a specific comment | Token |
| PATCH | `/api/posts/<id>/comments/<comment_id>/` | Update a comment | Token |
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
| Event | Endpoint | Description | Auth |
|-------|----------|-------------|------|
| GET | `/sessions/` | List all user's interview sessions | Required |
| POST | `/sessions/` | Create a new interview session | Required |
| GET | `/sessions/<id>/` | Get session details + all messages | Required |
| DELETE | `/sessions/<id>/` | Delete a session | Required |

### Calls (LiveKit)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/calls/` | List all rooms | Token |
| POST | `/api/calls/` | Create a room (employer only) | Token |
| GET | `/api/calls/<id>/` | Get room details | Token |
| PUT | `/api/calls/<id>/` | Update room (host only) | Token |
| DELETE | `/api/calls/<id>/` | Delete room (host only) | Token |
| POST | `/api/calls/<id>/token/` | Get LiveKit token to join | Token |
| GET | /api/calls/<id>/participants/ | List participants in a room | Token |

REST APIs were tested with Postman.
WebSocket connections were tested via https://websocketking.com

## Token-based authentication (temporary)

All protected APIs require a token in the request header:

```
Authorization: Token <your-token>
```
