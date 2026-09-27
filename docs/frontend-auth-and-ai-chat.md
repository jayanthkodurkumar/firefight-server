# Frontend integration: Auth & ticket AI chat

This document describes the **authentication** API and the **per-ticket AI chat** API for the Firefight backend. All ticket and chat routes require a valid JWT unless noted.

**Base URL (local dev):** `http://127.0.0.1:8000`  
**OpenAPI / Swagger:** `http://127.0.0.1:8000/docs`  
**Health (no auth):** `GET /health` → `{ "status": "ok" }`

**CORS:** Configure `CORS_ORIGINS` on the server (comma-separated). Defaults include `http://localhost:5173` and `http://localhost:3000`. Use `credentials: true` if you send cookies later; today auth is **Bearer token only**.

---

## Authentication

### Overview

- Email + password signup and login.
- **Login** (and only login) returns a **JWT access token** (`token_type: "bearer"`). Signup returns a success message only.
- Protected routes expect:  
  `Authorization: Bearer <access_token>`
- Token lifetime defaults to **24 hours** (`JWT_EXPIRE_MINUTES`, default `1440`).
- There is **no refresh token** in v1; re-login when the token expires.

### Endpoints

| Method | Path | Auth required |
|--------|------|----------------|
| `POST` | `/api/auth/signup` | No |
| `POST` | `/api/auth/login` | No |
| `POST` | `/api/auth/forgot-password` | No |
| `POST` | `/api/auth/reset-password` | No |

Ticket list, ticket detail, and all chat routes under `/api/tickets/...` require the Bearer token.

---

### `POST /api/auth/signup`

Create an account. **Does not** return a token — redirect the user to the login screen after success.

**Request body (JSON)**

| Field | Type | Rules |
|-------|------|--------|
| `email` | string | Valid email |
| `password` | string | 8–128 characters |

**Example**

```json
{
  "email": "engineer@example.com",
  "password": "securepass123"
}
```

**Success: `201 Created`**

```json
{
  "message": "Account created. Please log in."
}
```

**Errors**

| Status | `detail` (typical) |
|--------|---------------------|
| `409` | `Email already registered` |
| `422` | Validation error (invalid email, password too short) |

---

### `POST /api/auth/login`

**Request body (JSON)**

| Field | Type |
|-------|------|
| `email` | string |
| `password` | string |

**Example**

```json
{
  "email": "engineer@example.com",
  "password": "securepass123"
}
```

**Success: `200 OK`**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Errors**

| Status | `detail` |
|--------|----------|
| `401` | `Incorrect email or password` |

---

### `POST /api/auth/forgot-password`

Starts a password reset. Email delivery is not wired yet; in **dev**, the server may return the reset token in the JSON when `AUTH_EXPOSE_RESET_TOKEN=true` (default in example env).

**Request body**

```json
{
  "email": "engineer@example.com"
}
```

**Success: `200 OK`**

```json
{
  "message": "If that email is registered, a reset link has been sent.",
  "reset_token": "optional-dev-only-token-or-null"
}
```

`reset_token` is **`null` in production** when `AUTH_EXPOSE_RESET_TOKEN=false`. The message is the same whether or not the email exists (no user enumeration).

---

### `POST /api/auth/reset-password`

**Request body**

| Field | Type | Rules |
|-------|------|--------|
| `email` | string | Same email used in forgot-password |
| `reset_token` | string | 16–128 chars |
| `new_password` | string | 8–128 chars |

**Example**

```json
{
  "email": "engineer@example.com",
  "reset_token": "token-from-forgot-response-or-email",
  "new_password": "newsecurepass123"
}
```

**Success: `200 OK`**

```json
{
  "message": "Password updated"
}
```

**Errors**

| Status | `detail` (typical) |
|--------|---------------------|
| `400` | `Invalid reset request`, `Invalid reset token`, `Reset token expired` |

---

### Using the token on protected routes

```http
GET /api/tickets
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Errors (any protected route)**

| Status | `detail` |
|--------|----------|
| `401` | `Not authenticated` (missing/invalid header) |
| `401` | `Invalid or expired token` |
| `401` | `User not found` |

---

## Ticket AI chat

### Overview

- One **chat thread per user per ticket** (`ticket_id` is the public id, e.g. `TKT-A1B2C3D4`).
- History is stored in Postgres: only **user** and **assistant** text (no tool traces in the API).
- A single UI chat box; the backend **routes** each message to:
  - **QA agent** — read-only answers about the ticket, policy, signals, severity, etc.
  - **Allocation agent** — suggest technician dispatch; **does not write to the DB** until the user approves.
- When allocation proposes an assign, the API returns **`pending_action`**. The frontend should show a confirm UI and call **approve-assignment** to persist.

**Prerequisites**

- User is authenticated.
- Ticket exists (`404` if not).
- Chat LLM: server needs `OPENAI_API_KEY` (and optionally `CHAT_MODEL`, default `openai:gpt-4o-mini`). Misconfiguration may surface as `500` on send message.

All chat routes: prefix **`/api/tickets/{ticket_id}/chat`**, Bearer required.

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/tickets/{ticket_id}/chat/messages` | Load history |
| `POST` | `/api/tickets/{ticket_id}/chat/messages` | Send user message; get assistant reply |
| `POST` | `/api/tickets/{ticket_id}/chat/approve-assignment` | Confirm technician assignment (DB write) |
| `POST` | `/api/tickets/{ticket_id}/chat/reject-ticket` | Reject ticket (no dispatch); clears pending assign UI |

`{ticket_id}` is the string `ticket_id` field from the tickets API, not the internal UUID `id`.

---

### `GET /api/tickets/{ticket_id}/chat/messages`

**Request:** no body.

**Success: `200 OK`**

```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "role": "user",
      "content": "Why did this ticket open?",
      "pending_action": null,
      "created_at": "2026-03-27T12:00:00.000Z"
    },
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "role": "assistant",
      "content": "The ticket opened because...",
      "pending_action": null,
      "created_at": "2026-03-27T12:00:05.000Z"
    }
  ]
}
```

| Field | Type | Notes |
|-------|------|--------|
| `items[].role` | `"user"` \| `"assistant"` | |
| `items[].content` | string | Message text |
| `items[].pending_action` | object \| null | Set on assistant rows when allocation proposed an assign (same shape as below) |
| `items[].created_at` | ISO 8601 datetime | UTC |

If the user has never chatted on this ticket, `items` is `[]` (thread may not exist yet).

**Errors**

| Status | `detail` |
|--------|----------|
| `404` | `Ticket '…' not found` |
| `401` | Auth errors (see above) |

---

### `POST /api/tickets/{ticket_id}/chat/messages`

Send one user message; server loads prior history, runs the orchestrator, persists user + assistant rows, returns the new assistant reply.

**Request body**

| Field | Type | Rules |
|-------|------|--------|
| `message` | string | 1–8000 characters |

**Example**

```json
{
  "message": "Who can we send for this thermal ticket?"
}
```

**Success: `200 OK`**

```json
{
  "reply": "I recommend dispatching Jane Doe based on region and thermal specialty. Please confirm to assign.",
  "pending_action": {
    "action": "assign_technician",
    "ticket_id": "TKT-A1B2C3D4",
    "technician_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "technician_name": "Jane Doe",
    "notes": "Thermal S4; on-call preferred"
  }
}
```

| Field | Type | Notes |
|-------|------|--------|
| `reply` | string | Assistant message to show in the UI |
| `pending_action` | object \| null | Present when allocation called `propose_assignment`; **`null` for QA-only turns** |

**`pending_action` shape (when present)**

| Field | Type | Description |
|-------|------|-------------|
| `action` | `"assign_technician"` | Fixed discriminator |
| `ticket_id` | string | Public ticket id |
| `technician_id` | string | UUID string — pass to approve endpoint |
| `technician_name` | string | Display name |
| `notes` | string | Dispatch notes suggested by the agent |

**Frontend flow**

1. Append user message locally (optional; server already stored it).
2. Show `reply` as assistant message.
3. If `pending_action` is non-null, show **Approve / Cancel** (or edit notes then approve).
4. On approve → `POST .../approve-assignment` with `technician_id` (and optional `notes`).
5. After approve, ticket is assigned in DB; a new allocation proposal may fail if the ticket is already assigned.

**Errors**

| Status | `detail` |
|--------|----------|
| `404` | Ticket not found |
| `422` | Empty/too long message |
| `500` | LLM/runtime error (message in `detail`) |

---

### `POST /api/tickets/{ticket_id}/chat/approve-assignment`

Writes assignment to the ticket: **assigned technician** + **assigned by** (current user), and sets ticket **`status`** to **`assigned`**. This is the only chat path that mutates ticket assignment.

**Request body**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `technician_id` | string | Yes | UUID from `pending_action.technician_id` (or user override if product allows) |
| `notes` | string \| null | No | Dispatch notes stored on the ticket |

**Example**

```json
{
  "technician_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "notes": "Thermal S4; on-call preferred"
}
```

**Success: `200 OK`**

```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "status": "assigned",
  "technician_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "technician_name": "Jane Doe"
}
```

Ticket status values: `open` → `assigned` (on approve) or `rejected` (on reject) → `resolved` (future).

**Errors**

| Status | `detail` (typical) |
|--------|---------------------|
| `400` | `Invalid technician_id` |
| `400` | `Ticket already assigned`, `Technician not found`, `Ticket '…' not found` |
| `404` | Ticket not found (unknown `ticket_id`) |

**Note:** The backend does not yet require that `technician_id` matches the latest `pending_action`; the UI should still prefer the proposed id for safety.

---

### `POST /api/tickets/{ticket_id}/chat/reject-ticket`

Decline dispatch for an **open** ticket (e.g. “Dismiss” on the assignment card, or a separate reject control). Sets **`status`** to **`rejected`**, stores optional reason, clears **`pending_action`** on chat history for this user.

**Request body**

| Field | Type | Required |
|-------|------|----------|
| `reason` | string \| null | No (max 2000 chars) |

**Example**

```json
{
  "reason": "False positive — comms recovered after reboot"
}
```

**Success: `200 OK`**

```json
{
  "ticket_id": "TKT-A1B2C3D4",
  "status": "rejected",
  "rejection_reason": "False positive — comms recovered after reboot"
}
```

**Errors**

| Status | `detail` (typical) |
|--------|---------------------|
| `400` | `Ticket already rejected`, `Cannot reject an assigned ticket`, `Cannot reject a resolved ticket` |
| `404` | Ticket not found |

After reject, do not show the approve card; refresh ticket header to show `rejected`.

---

## Suggested UI integration checklist

1. **Auth**
   - Signup → show success message, then navigate to login (no token).
   - Login → store `access_token` (memory, secure storage, or httpOnly cookie if you add a BFF later).
   - Attach `Authorization: Bearer …` to all `/api/tickets/*` requests.
   - Handle `401` → redirect to login.

2. **Ticket page**
   - Load ticket detail from `GET /api/tickets/{ticket_id}` (auth required).
   - On panel open: `GET .../chat/messages` and render `items` in order.

3. **Send message**
   - `POST .../chat/messages` with `{ "message": "..." }`.
   - Render `reply`; if `pending_action`, show confirmation affordance.

4. **Approve assignment**
   - `POST .../approve-assignment` with `technician_id` and optional `notes`.
   - Refresh ticket detail if you display assignee (assignment fields on ticket detail may be added later).

5. **Per-user history**
   - Two users on the same ticket see **different** chat histories (scoped by logged-in user).

---

## Related ticket APIs (auth required)

For context when building the ticket page:

- `GET /api/tickets` — list with pagination/filters
- `GET /api/tickets/{ticket_id}` — detail

See Swagger for query params and response shapes. Assignment fields (`assigned_technician_id`, `assigned_by_user_id`, `dispatch_notes`, `assigned_at`) may not all be exposed on `TicketDetail` yet; approve response confirms the assignee.

---

## Example sequence (curl)

```bash
# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"engineer@example.com","password":"securepass123"}' \
  | jq -r .access_token)

# History
curl -s http://127.0.0.1:8000/api/tickets/TKT-EXAMPLE/chat/messages \
  -H "Authorization: Bearer $TOKEN"

# Chat
curl -s -X POST http://127.0.0.1:8000/api/tickets/TKT-EXAMPLE/chat/messages \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"message":"Summarize this ticket"}'

# Approve (after pending_action)
curl -s -X POST http://127.0.0.1:8000/api/tickets/TKT-EXAMPLE/chat/approve-assignment \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"technician_id":"<uuid>","notes":"Approved from UI"}'
```

---

## Questions / changes

For contract changes, prefer the live OpenAPI spec at `/docs` or `/openapi.json`. Backend contact can extend `TicketDetail` with assignment fields when the UI needs them on the ticket header without a separate approve response.
