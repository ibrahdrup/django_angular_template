# Airport Operations Management System — Django + Angular

Full implementation of the Airport Operations Management System exam (Parts A–E):
flight scheduling, gate allocation with a mandatory 30-minute turnaround buffer, RBAC across four
roles, service requests with state machines, cascading departure release, audit trail, and
reporting.

- **Backend**: Django 4.2 + Django REST Framework, JWT auth (`djangorestframework-simplejwt`),
  MySQL database.
- **Frontend**: Angular 18 (standalone components).
- **No Docker is used or required.** The backend connects to a normal, natively-installed MySQL
  server on the standard port `3306`.

---

## 1. Prerequisites

- Python 3.10+
- Node.js 20.x and npm (Angular CLI is used via `npx`, no global install needed)
- A MySQL server (8.0 recommended) running locally on port 3306

### Installing MySQL

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

**Windows:**
- Download and run the MySQL Installer from https://dev.mysql.com/downloads/installer/
  (choose the "MySQL Server" component), or install via Chocolatey:
  ```powershell
  choco install mysql
  ```
- Start the "MySQL" service from Services (services.msc) or `net start MySQL`.

### Create the database and app user

Connect as root and run:

```bash
mysql -u root -p
```

```sql
CREATE DATABASE airport_ops_db CHARACTER SET utf8mb4;
CREATE USER 'airport_ops_user'@'localhost' IDENTIFIED BY 'airport_ops_pass';
GRANT ALL PRIVILEGES ON airport_ops_db.* TO 'airport_ops_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

(On Windows, run the same commands from the "MySQL Command Line Client" or MySQL Workbench.)

---

## 2. Backend setup (Django + DRF)

```bash
cd django-angular/backend
python3 -m venv .venv

# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Database driver note
`mysqlclient` (the C-extension MySQL driver) requires MySQL's native dev headers
(`libmysqlclient-dev` / `mysql_config`) to build. To keep setup friction-free on any machine,
this project uses **PyMySQL** (pure-Python, installed via `requirements.txt`) as the MySQL driver,
activated with `pymysql.install_as_MySQLdb()` in `backend/config/__init__.py`. If you prefer
`mysqlclient` and have the build headers available, you can `pip install mysqlclient`, remove the
`pymysql` shim from `config/__init__.py`, and it will work as a drop-in replacement.

### Environment variables

`backend/.env` (already present, edit if your MySQL credentials differ):

```
DEBUG=True
SECRET_KEY=django-insecure-airport-ops-exam-secret-key-change-me
DB_NAME=airport_ops_db
DB_USER=airport_ops_user
DB_PASSWORD=airport_ops_pass
DB_HOST=localhost
DB_PORT=3306
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

### Migrate, seed, run

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

The API is now available at `http://localhost:8000/api/v1/`.
Swagger/OpenAPI schema: `http://localhost:8000/api/schema/`, Swagger UI: `http://localhost:8000/api/docs/`.
Django admin: `http://localhost:8000/admin/` (log in with the seeded `admin` account).

### Seeded login credentials

| Role | Username | Password |
|---|---|---|
| admin | `admin` | `Admin@12345` |
| gate_controller | `gatecontroller` | `Controller@12345` |
| ground_staff | `groundstaff` | `GroundStaff@12345` |
| passenger | `passenger` | `Passenger@12345` |

`seed_demo` also creates 5 gates (domestic/international/cargo, one under maintenance), 4 flights,
2 gate assignments, and 2 service requests.

### Running tests

```bash
python manage.py test
```

30 tests covering the gate overlap/buffer algorithm, the flight and service-request state
machines, cascading departure release, and API-level auth/RBAC/business-rule scenarios.

---

## 3. Frontend setup (Angular 18)

```bash
cd django-angular/frontend
npm install
npx ng serve
```

Open `http://localhost:4200`. The frontend expects the backend at `http://localhost:8000/api/v1`
(see `src/environments/environment.ts`).

To produce a production build:

```bash
npx ng build
```

Output is written to `frontend/dist/frontend`.

---

## 4. Default ports

| Service | Port |
|---|---|
| MySQL | 3306 |
| Django backend | 8000 |
| Angular frontend | 4200 |

---

## 5. Project layout

```
django-angular/
├── README.md
├── LEARNING_GUIDE.md          # step-by-step system flow for exam study
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env
│   ├── config/                # Django project settings, urls, wsgi
│   └── core/                  # the single Django app: models, views, serializers,
│                               # services (business rules), permissions, tests
└── frontend/
    └── src/app/
        ├── core/               # services, guards, interceptors, models
        ├── shared/nav/         # sidebar + session-expiry timer
        └── pages/              # login, register, dashboard, service-requests, reports, admin
```

---

## 6. Notable design decisions / gaps

- **Password hashing**: Django's `BCryptSHA256PasswordHasher` is configured as the primary hasher
  (`PASSWORD_HASHERS` in `settings.py`), satisfying the "bcrypt, cost factor ≥ 10" requirement.
  PBKDF2 remains as a fallback verifier for any pre-existing hashes.
- **`flight_type` field**: the exam spec's `flights` table doesn't include an explicit
  domestic/international/cargo field, yet the gate-type-matching rule requires one to determine a
  flight's type. A `flight_type` field (same enum as `gates.gate_type`) was added to the `Flight`
  model to make this rule enforceable — this is the one deliberate schema addition beyond the spec.
- **API docs**: `drf-spectacular` installed cleanly; Swagger UI is live at `/api/docs/`.
- **CSV export param**: the report endpoint uses `?export=csv` rather than `?format=csv`, because
  DRF reserves the `format` query parameter for its own content-negotiation and a value of `csv`
  with no CSV renderer registered produces a 404, not the report.
- **Verification note**: this sandbox has no natively-installed MySQL server and no root/sudo to
  install one, so end-to-end verification (migrate/seed/tests/curl) was run against a temporary,
  throwaway MySQL 8.0 container used purely as a private test harness and discarded afterwards —
  no Docker file ships with this project, and the shipped configuration
  (`.env`, `settings.py`) targets a plain local MySQL install on port 3306 as described above.
