# Airport Operations Management System — From-Scratch Build Tutorial

This is a strictly sequential, numbered build guide. Follow it top to bottom starting from an
empty folder and you will reproduce this exact, working, fully-tested project: Django 4.2 + DRF
backend on MySQL (native, no Docker), JWT auth, RBAC across four roles, gate-overlap/buffer
business rules, two state machines, cascading departure release, audit trail, reporting, and an
Angular 18 standalone-component frontend. Every file shown below is the **real, complete file**
from this repository — nothing is paraphrased or abbreviated. Where a design choice matters, it is
noted in one short parenthetical on that step, not a separate essay.

Prerequisites: Python 3.10+, Node.js 20.x + npm, a MySQL 8.0 server running locally on port 3306
with root access to create a database and user.

---

## Part 1 — Backend project scaffold

### Step 1 — Create the project root

```bash
mkdir -p airport-ops-system/django-angular
cd airport-ops-system/django-angular
```

### Step 2 — Create the backend folder and a virtual environment

```bash
mkdir backend
cd backend
python3 -m venv .venv
```

### Step 3 — Activate the virtual environment

```bash
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

### Step 4 — Write `backend/requirements.txt`

```text
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
PyJWT
django-cors-headers==4.3.0
drf-spectacular
django-filter
bcrypt
PyMySQL
cryptography
```

### Step 5 — Install dependencies

```bash
pip install -r requirements.txt
```

(`PyMySQL` is used instead of `mysqlclient` — `mysqlclient` is a C extension that needs MySQL's
native dev headers/`mysql_config` to build, which are often missing on a fresh machine; PyMySQL is
pure-Python and works everywhere with zero build step, at the cost of being a bit slower.)

### Step 6 — Create the Django project

```bash
django-admin startproject config .
```

This generates `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`,
`config/wsgi.py`, and `config/asgi.py` with Django's stock boilerplate. `manage.py` is left exactly
as generated:

```python
#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
```

`config/wsgi.py` (generated, unmodified):

```python
"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
```

`config/asgi.py` (generated, unmodified):

```python
"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
```

### Step 7 — Create the `core` app

```bash
python manage.py startapp core
```

This generates `core/__init__.py` (empty), `core/apps.py`, `core/admin.py` (stub), `core/models.py`
(stub), `core/tests.py` (single stub file — replaced by a `tests/` package in Step 31), `core/views.py`
(stub), and `core/migrations/__init__.py`. `core/apps.py` is left exactly as generated:

```python
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
```

Register the app immediately in `config/settings.py`'s `INSTALLED_APPS` — done together with the
rest of settings in Step 11.

### Step 8 — Activate the PyMySQL driver shim

Edit `config/__init__.py`:

```python
import pymysql

pymysql.install_as_MySQLdb()
```

This must run before Django touches the database, which is why it lives in the package
`__init__.py` — the first file Python imports when anything does `import config`.

### Step 9 — Create `backend/.env`

```env
DEBUG=True
SECRET_KEY=django-insecure-airport-ops-exam-secret-key-change-me
DB_NAME=airport_ops_db
DB_USER=airport_ops_user
DB_PASSWORD=airport_ops_pass
DB_HOST=localhost
DB_PORT=3306
CORS_ALLOWED_ORIGINS=http://localhost:4200
```

### Step 10 — Write `core/models.py`

All six tables live in one file. `User` must exist before `AUTH_USER_MODEL` is set in Step 11, so
models come first.

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        GATE_CONTROLLER = "gate_controller", "Gate Controller"
        GROUND_STAFF = "ground_staff", "Ground Staff"
        PASSENGER = "passenger", "Passenger"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PASSENGER, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.username} ({self.role})"


class Gate(models.Model):
    class GateType(models.TextChoices):
        DOMESTIC = "domestic", "Domestic"
        INTERNATIONAL = "international", "International"
        CARGO = "cargo", "Cargo"

    class Status(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        UNDER_MAINTENANCE = "under_maintenance", "Under Maintenance"
        CLOSED = "closed", "Closed"

    gate_number = models.CharField(max_length=10, unique=True)
    terminal = models.CharField(max_length=50)
    gate_type = models.CharField(max_length=20, choices=GateType.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPERATIONAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.gate_number


class Flight(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ASSIGNED = "assigned", "Assigned"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        CANCELLED = "cancelled", "Cancelled"
        ARRIVED = "arrived", "Arrived"

    flight_no = models.CharField(max_length=10, unique=True, db_index=True)
    airline = models.CharField(max_length=100)
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    aircraft_type = models.CharField(max_length=50)
    scheduled_arrival = models.DateTimeField()
    scheduled_departure = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    flight_type = models.CharField(
        max_length=20,
        choices=Gate.GateType.choices,
        default=Gate.GateType.DOMESTIC,
        help_text="Determines which gate types this flight may be assigned to.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.flight_no


class GateAssignment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        ASSIGNED = "assigned", "Assigned"
        DELAYED = "delayed", "Delayed"
        BOARDING = "boarding", "Boarding"
        DEPARTED = "departed", "Departed"
        CANCELLED = "cancelled", "Cancelled"

    gate = models.ForeignKey(Gate, on_delete=models.CASCADE, related_name="assignments")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="gate_assignments")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="assignments_made"
    )
    notes = models.TextField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["gate", "start_time", "end_time"], name="idx_gate_start_end"),
            models.Index(fields=["gate", "start_time"], name="idx_gate_start"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F("end_time")),
                name="gate_assignment_start_before_end",
            )
        ]

    def __str__(self):
        return f"{self.flight.flight_no} @ {self.gate.gate_number}"


class ServiceRequest(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", "Food"
        BEVERAGE = "beverage", "Beverage"
        WHEELCHAIR = "wheelchair", "Wheelchair"
        SPECIAL_ASSISTANCE = "special_assistance", "Special Assistance"
        MEDICAL = "medical", "Medical"
        LOST_BAGGAGE = "lost_baggage", "Lost Baggage"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    passenger = models.ForeignKey(User, on_delete=models.CASCADE, related_name="service_requests")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name="service_requests")
    flight_no = models.CharField(max_length=10)
    category = models.CharField(max_length=30, choices=Category.choices)
    details = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_requests"
    )
    resolution_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["passenger", "status"], name="idx_passenger_status"),
        ]

    def __str__(self):
        return f"SR#{self.id} {self.category} ({self.status})"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=50, null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
```

(`flight_type` is a deliberate addition beyond a literal spec field list — the gate-type-matching
rule in Step 18's service layer needs some field on `Flight` to compare against `Gate.gate_type`.)

(The composite index `idx_gate_start_end` and the `start_time < end_time` check constraint exist
specifically to support the overlap-buffer query in Step 18 — a `UNIQUE` constraint cannot express
"no two time ranges may overlap".)

### Step 11 — Write `config/settings.py`

```python
"""
Django settings for the Airport Operations Management System backend.
"""

import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-airport-ops-exam-secret-key-change-me")

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "airport_ops_db"),
        "USER": os.environ.get("DB_USER", "airport_ops_user"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "airport_ops_pass"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_USER_MODEL = "core.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# bcrypt-strength hashing: BCryptSHA256PasswordHasher is listed first so it is
# the algorithm used for all newly-set passwords (cost factor >= 10 default).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "URL_FORMAT_OVERRIDE": None,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "10/min",
        "auth_register": "10/min",
    },
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "core.serializers.CustomTokenObtainPairSerializer",
}

CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "http://localhost:4200"
).split(",")
CORS_ALLOW_CREDENTIALS = True

SPECTACULAR_SETTINGS = {
    "TITLE": "Airport Operations Management System API",
    "DESCRIPTION": "Flight scheduling, gate allocation, service requests, RBAC.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
```

Notes tied directly to lines above: `AUTH_USER_MODEL = "core.User"` only works because `User` was
defined in Step 10 before Django's app registry loads; `EXCEPTION_HANDLER` and
`TOKEN_OBTAIN_SERIALIZER` are dotted-path strings resolved lazily, so it is fine that
`core/exceptions.py` and `core/serializers.py` do not exist yet — they must exist by the time a
request is served (Steps 15 and 19), not by the time settings.py is imported. `CorsMiddleware` is
inserted second in `MIDDLEWARE`, immediately after `SecurityMiddleware` and before anything that
might generate a response, per django-cors-headers' requirement that it run early. Never set
`CORS_ALLOW_ALL_ORIGINS = True` on anything issuing JWTs.

### Step 12 — Generate the migration

```bash
python manage.py makemigrations core
```

`makemigrations` only diffs `models.py` against migration history — it needs `INSTALLED_APPS` and
`AUTH_USER_MODEL` from Step 11 to resolve the app, but not a live database connection. This writes
`core/migrations/0001_initial.py`, which Django generates as:

```python
# Generated by Django 4.2.7 on 2026-09-17 06:17

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("admin", "Admin"),
                            ("gate_controller", "Gate Controller"),
                            ("ground_staff", "Ground Staff"),
                            ("passenger", "Passenger"),
                        ],
                        db_index=True,
                        default="passenger",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "abstract": False,
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Flight",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "flight_no",
                    models.CharField(db_index=True, max_length=10, unique=True),
                ),
                ("airline", models.CharField(max_length=100)),
                ("origin", models.CharField(max_length=100)),
                ("destination", models.CharField(max_length=100)),
                ("aircraft_type", models.CharField(max_length=50)),
                ("scheduled_arrival", models.DateTimeField()),
                ("scheduled_departure", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("assigned", "Assigned"),
                            ("delayed", "Delayed"),
                            ("boarding", "Boarding"),
                            ("departed", "Departed"),
                            ("cancelled", "Cancelled"),
                            ("arrived", "Arrived"),
                        ],
                        default="scheduled",
                        max_length=20,
                    ),
                ),
                (
                    "flight_type",
                    models.CharField(
                        choices=[
                            ("domestic", "Domestic"),
                            ("international", "International"),
                            ("cargo", "Cargo"),
                        ],
                        default="domestic",
                        help_text="Determines which gate types this flight may be assigned to.",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Gate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("gate_number", models.CharField(max_length=10, unique=True)),
                ("terminal", models.CharField(max_length=50)),
                (
                    "gate_type",
                    models.CharField(
                        choices=[
                            ("domestic", "Domestic"),
                            ("international", "International"),
                            ("cargo", "Cargo"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("under_maintenance", "Under Maintenance"),
                            ("closed", "Closed"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("action", models.CharField(max_length=100)),
                ("entity_type", models.CharField(max_length=50)),
                ("entity_id", models.CharField(blank=True, max_length=50, null=True)),
                ("details", models.TextField(blank=True, null=True)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ServiceRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("flight_no", models.CharField(max_length=10)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("food", "Food"),
                            ("beverage", "Beverage"),
                            ("wheelchair", "Wheelchair"),
                            ("special_assistance", "Special Assistance"),
                            ("medical", "Medical"),
                            ("lost_baggage", "Lost Baggage"),
                            ("other", "Other"),
                        ],
                        max_length=30,
                    ),
                ),
                ("details", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("in_progress", "In Progress"),
                            ("resolved", "Resolved"),
                            ("rejected", "Rejected"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("resolution_notes", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "flight",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_requests",
                        to="core.flight",
                    ),
                ),
                (
                    "passenger",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="service_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["passenger", "status"], name="idx_passenger_status"
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="GateAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("assigned", "Assigned"),
                            ("delayed", "Delayed"),
                            ("boarding", "Boarding"),
                            ("departed", "Departed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="assigned",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True, null=True)),
                ("is_deleted", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "flight",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gate_assignments",
                        to="core.flight",
                    ),
                ),
                (
                    "gate",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="core.gate",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["gate", "start_time", "end_time"],
                        name="idx_gate_start_end",
                    ),
                    models.Index(fields=["gate", "start_time"], name="idx_gate_start"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="gateassignment",
            constraint=models.CheckConstraint(
                check=models.Q(("start_time__lt", models.F("end_time"))),
                name="gate_assignment_start_before_end",
            ),
        ),
    ]
```

### Step 13 — Create the MySQL database and app user

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

(MySQL was chosen because the exam specified it; the same `django.db.backends.mysql` engine works
identically against MariaDB if that's what's actually installed.)

### Step 14 — Apply the migration

```bash
python manage.py migrate
```

This creates all six tables (plus Django/DRF's own `auth_group`, `django_session`,
`token_blacklist_*`, etc.) in `airport_ops_db`. If this fails with a connection error, re-check
Step 9's `.env` values and that `mysqld` is running on port 3306.

