# job-platform-backend

## Technologies

- Docker
- Python 3.14
- Django 6.0, DRF
- PostgreSQL
- MinIO

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
| GET | `/api/users/me/` | Get current user info including avatar | Token |
| PATCH | `/api/users/me/` | Update avatar, first name, last name, email | Token |
| GET | `/api/users/<id>/` | Get public user info | Token |

### Candidates
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/candidates/<id>/` | Get candidate profile | Token |
| GET | `/api/candidates/me/` | Get current user's candidate profile | Token |
| PUT | `/api/candidates/me/` | Update current user's candidate profile | Token |

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
| POST | `/api/posts/<id>/like/` | Like a post | Token |
| DELETE | `/api/posts/<id>/like/` | Unlike a post | Token |
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

### Calls
| Event | Endpoint | Description | Auth |
|-------|----------|-------------|------|
| GET | `/api/calls/` | List all available call rooms
| POST | `/api/calls/` | Create a new room (Restricted to Employers; includes past-date validation)
| GET | `/api/calls/<id>/` | Get room details
| PUT | `/api/calls/<id>/` | Update room (Restricted to Room Host)
| DELETE | `/api/calls/<id>/` | Delete room (Restricted to Room Host)

### WebSocket
| Event | Endpoint | Description | Auth |
|-------|----------|-------------|------|
| Connect | `ws://.../ws/conversations/<id>/?token=<token>` | Connect to a conversation | Token |
| Send | `{"content": "..."}` | Send a message | - |
| Receive (message) | `{"type": "message", "message_id": ..., "content": ..., "sender_id": ..., "sender_username": ..., "created_at": ...}` | Incoming message | - |
| Receive (read) | `{"type": "read", "reader_id": ..., "reader_username": ...}` | Read receipt | - |
| Connect | `ws://<host>:8000/ws/calls/<room_id>/?token=<token>` | Join a call room | Token |
| Receive | `{"type": "user_joined", "username": ..., "users": [...]}` | User joined broadcast with user list | - |
| Receive | `{"type": "user_left", "username": ..., "users": [...]}` | User left broadcast | - |
| Send | `{"type": "offer", "target": "...", "offer": {...}}` | WebRTC offer | - |
| Send | `{"type": "answer", "target": "...", "answer": {...}}` | WebRTC answer | - |
| Send | `{"type": "ice_candidate", "target": "...", "candidate": {...}}` | ICE candidate | - |
| Send | `{"type": "kick", "user_id": <id>}` | Host removes a user | Host Only |

### Video Calls (WebRTC Signaling)
The calls WebSocket supports WebRTC peer-to-peer video calling:

1. Connect to room with token
2. Wait for `user_joined` events to know who's in the room
3. Initiate calls by sending `offer` to target users
4. Handle incoming `offer` with `answer`
5. Exchange `ice_candidate` for NAT traversal

**Race condition prevention**: Only the user with alphabetically lower username initiates the call. this is still under work and will change in the future (its in the front end and the front end is still underdevelopment).

**Custom Error Codes:**
* `4001`: Authentication failed (No/Invalid Token)
* `4003`: Meeting date is in the future / User was kicked
* `4004`: Room is inactive (Host has not joined yet)

REST APIs were tested with Postman.
WebSocket connections were tested via https://websocketking.com

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
| `MINIO_USER` | MinIO username (Default: jobplatform) |
| `MINIO_PASSWORD` | MinIO password (Default: jobplatform) |
| `MINIO_BUCKET` | MinIO bucket name (Default: jobplatform) |

## Progress

- Implemented most of use cases 1 and 2
- Missing: CV upload, Profile score calculation (We need to decide where calculation should happen)
- Added tests to jobs/test.py to check if everything is working as its supposed to
- Added reviews and some tests in reviews/tests.py
- Added social networking and some tests in social/tests.py
- Added messaging with WebSocket connections and some tests in messaging/tests.py
- Added support for deleting conversations and messages in messaging app
