# PyOS — Web Application

A full-stack "virtual operating system" workspace: a Django REST backend and a
React (Vite) frontend implementing user management, a virtual filesystem,
search, command history, a recycle bin, and an activity log.

```
pyos/
├── backend/    Django + DRF REST API (JWT auth, virtual filesystem, logs) + postgresql for database
├── frontend/   React SPA (login, dashboard, explorer, editor, search, ...)
```

### First run — creating the admin
The database starts empty. Open the app, click **Register**, and create an
account: **the first account created automatically becomes the system
administrator** (it gets the Admin Panel, the sudo override, and the system-wide
log view). Every account registered afterwards is a standard user. Register a
second account to try the sharing / access-control features between two users.

## Architecture

### Backend (Django + DRF)
- **apps/accounts** — custom `User` model, JWT auth (login/refresh/register),
  `/me`, and an admin-only user-management dashboard. The first account to
  register is automatically promoted to administrator; every later registration
  is a standard user. The user list is annotated with per-user `files_created`,
  `directories_created`, and `space_used` (total content size), and admins can
  deactivate (block login), promote to admin / revoke admin, or delete any user.
  Promoting keeps Django's `is_staff` in sync with the app-level `is_admin_role`,
  and an admin cannot revoke or deactivate their own account (to avoid locking
  themselves out).
- **apps/filesystem** — the `Node` model is a self-referential tree where each
  node is a directory or a file, with a `permission_level` of private,
  read-only, or public. One `NodeViewSet` exposes CRUD plus actions for
  directory listing, search, soft-delete (recycle bin), restore, purge, and
  dashboard stats. Deletion is recursive and reversible.
- **apps/core** — append-only `ActivityLog` (written via a `log_action` helper)
  and `CommandHistory`. The log endpoint takes a `?scope=all|me` toggle for
  admins to audit the whole system or just themselves. A second helper,
  `notify_owner`, writes an **owner notice** whenever someone acts on a file or
  folder they don't own (admin sudo actions, or a non-owner editing a public
  item): the owner sees an entry in *their own* log like "root (admin) updated
  'notes.txt' in your /home/alice", phrased from their point of view and showing
  who did it (name + role). It only fires when actor ≠ owner, so users never get
  notices about their own actions, and one user never sees a feed of activity on
  *another* user's files — only events touching their own.

### Terminal (the CLI, ported to the web)
The original PyOS was a command-line simulator. Its command set lives on in the
web app as a real, stateful terminal:
- `apps/filesystem/commands.py` is a `CommandEngine` that runs `pwd`, `ls`,
  `tree`, `cd`, `mkdir`, `touch`, `cat`, `echo "..." > file` (and `>>`),
  `rm [-r]`, `chmod`, `whoami`, `history`, `help`, and `clear` against the
  database-backed `Node` tree — so anything done in the terminal also appears in
  the Explorer (shared filesystem). It enforces the same permissions as the rest
  of the app. `tree` renders the logged-in user's entire directory tree (their
  own nodes only — never another user's).
- The terminal is **stateful** like a real shell: the client sends its current
  working directory with each command and the engine returns the new one, so
  `cd` / `pwd` behave naturally. `POST /api/terminal/run/` is the entry point.
- On registration, each user gets a **home directory** (`/home/<username>` plus a
  starter `welcome.txt`) via `apps/filesystem/scaffolding.py`, mirroring the
  CLI's per-user home. Both the top-level `home` directory **and** the user's own
  `home/<username>` directory are protected system folders that cannot be deleted
  (via the API or the terminal), exactly like `/home` and `/home/<you>` in a real
  OS; everything inside the user's home is freely removable.

The Explorer's root level shows each user only their own top-level folders plus
any folders other users have explicitly shared (read-only/public). Admins keep
their sudo override for opening and editing any node directly, but the root view
is intentionally per-user so it isn't a merged dump of everyone's home.

### Admin: All Workspaces
Admins get a dedicated **All Workspaces** screen (hidden from regular users).
The top level lists every user as a folder; opening one browses that user's full
filesystem — including their private files (full sudo). The admin can create,
edit, and delete anything there. Files/folders the admin creates inside a user's
workspace are **owned by that user** (the admin acts inside their space, like
`root` in `/home/<user>`). The protected `home`/`home/<user>` folders stay
undeletable even here. Backed by `GET /api/nodes/workspaces/` (the user list)
and `GET /api/nodes/workspace/?user=<id>&parent=<id>` (browse a user's tree),
both admin-only. Creating with an `owner_id` is honored only for admins; a
regular user's nodes are always forced to their own ownership.

### Access control (who can see / do what)
- **Visibility**: a user sees their own nodes plus any other user's nodes marked
  read-only or public. Admins (`is_admin_role` or `is_staff`) see *all* nodes —
  the "sudo" override.
- **Nested sharing (path traversal)**: a public/read-only item is reachable by
  other users even when it lives inside an otherwise-private home — like real
  Unix, where a shared file deep in `/home/alice` is readable because the path is
  traversable. Crucially, visibility *tunnels*: opening a shared folder reveals
  only its shared children, never the owner's private siblings. Sharing does not
  cascade — each item's own `permission_level` decides, so you explicitly mark
  exactly what you want exposed. Others reach shared items two ways: by browsing
  into a shared folder, or via the **"Shared with me"** view, which lists the
  topmost shared item in each chain (`GET /api/nodes/shared_with_me/`).
- **Editing**: owners and admins can always edit; a *public* node is editable by
  any logged-in user; *read-only* and *private* nodes reject non-owner edits
  with HTTP 403.
- **Deleting / re-sharing**: restricted to the owner or an admin, even for
  public nodes, so a shared file can't be removed out from under its owner.
- The serializer returns `is_owner` and `can_edit` per node so the frontend can
  render the right controls without guessing.

Authorization: every endpoint requires JWT auth; user management and the
system-wide log require an admin role.

### API summary
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/auth/register/` | Create account |
| POST | `/api/auth/login/` | Obtain JWT pair |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Current user |
| GET/POST | `/api/auth/users/` | User dashboard w/ usage stats · create (admin) |
| PATCH/DELETE | `/api/auth/users/<id>/` | Deactivate, promote/revoke admin, or delete a user (admin) |
| GET | `/api/nodes/?parent=<id>` | List a directory (incl. others' shared nodes) |
| POST | `/api/nodes/` | Create file/folder |
| GET/PATCH/DELETE | `/api/nodes/<id>/` | Read/edit/soft-delete (permission-checked) |
| GET | `/api/nodes/search/?q=` | Search name + content |
| GET | `/api/nodes/shared_with_me/` | Items others shared with you |
| GET | `/api/nodes/workspaces/` | All users as workspaces (admin) |
| GET | `/api/nodes/workspace/?user=<id>` | Browse a user's tree (admin) |
| GET | `/api/nodes/recycle_bin/` | Deleted items |
| POST | `/api/nodes/<id>/restore/` | Restore from bin |
| DELETE | `/api/nodes/<id>/purge/` | Permanent delete |
| GET | `/api/nodes/stats/` | Dashboard counts |
| GET/POST | `/api/commands/` | Command history |
| POST | `/api/terminal/run/` | Run a terminal command (CLI engine) |
| GET | `/api/logs/?scope=all\|me` | Activity log (scope toggle for admins) |

### Frontend (React + Vite)
React Router SPA. `AuthContext` holds the session and JWTs (in memory); an axios
client attaches the token and transparently refreshes on 401. Pages: Login,
Dashboard, Explorer (breadcrumb navigation, create/delete, a "My files" vs.
"Shared with me" toggle, a per-item "share" control for setting
private/read-only/public, and badges showing the owner of shared items), File
editor (load/save with Ctrl+S, read-only mode for shared
files you can't edit), Search, a **Terminal** (an interactive shell that runs
the ported CLI commands against your real files, with a live prompt that tracks
the working directory, up/down arrow command recall, and the saved command
history below), Recycle bin, Logs (with a system-wide vs. my-activity toggle for
admins), and an **Admin Panel** tab that only appears for admins (user dashboard
with usage stats, plus deactivate, promote/revoke admin, and delete).
The visual theme is a dark terminal/OS aesthetic with JetBrains Mono for chrome.

## Tests
```bash
cd backend
python manage.py test
```
14 tests covering auth flows (register/login, first-user admin setup, and protected endpoint access), filesystem CRUD (create directory/file), recursive soft delete, recycle bin, restore, search, per-user isolation, and access control for private, read-only, and public nodes, including non-owner permission restrictions.
