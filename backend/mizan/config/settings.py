"""Django settings, built from the typed environment in ``mizan.config.env``."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

from mizan.config.env import env

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
ENV = env

SECRET_KEY = env.secret_key
DEBUG = env.debug
ALLOWED_HOSTS = env.allowed_hosts_list

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "ninja",
    "procrastinate.contrib.django",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.headless",
    "mizan.platform",
    "mizan.apps.identity",
    "mizan.apps.org",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "mizan.platform.middleware.RequestContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "mizan.apps.identity.middleware.PrincipalMiddleware",
]

ROOT_URLCONF = "mizan.config.urls"
ASGI_APPLICATION = "mizan.config.asgi.application"
WSGI_APPLICATION = "mizan.config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]


def _database_from_url(url: str) -> dict[str, object]:
    parsed = urlparse(url)
    if parsed.scheme not in ("postgres", "postgresql"):
        raise ValueError("DATABASE_URL must be a postgresql:// URL")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
        "CONN_MAX_AGE": env.conn_max_age,
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,  # tenant scope opens the request transaction itself
        "TEST": {"NAME": f"test_{parsed.path.lstrip('/')}"},
    }


DATABASES = {"default": _database_from_url(env.database_url)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "identity.User"
SILENCED_SYSTEM_CHECKS = ["auth.W004"]  # e-mail is unique per tenant, not globally
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# django-allauth: browser realm (sessions, MFA/TOTP, passkeys). Signup is closed: users are
# created by staff (SPEC §7.1, §28).
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_ADAPTER = "mizan.apps.identity.allauth.AccountAdapter"
ACCOUNT_RATE_LIMITS = {"login_failed": "5/5m/ip,5/5m/key"}
HEADLESS_ONLY = True
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": env.app_base_url + "/auth/verify-email/{key}",
    "account_reset_password_from_key": env.app_base_url + "/auth/reset-password/{key}",
    "account_signup": env.app_base_url + "/auth/signup",
}
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes", "webauthn"]
MFA_PASSKEY_LOGIN_ENABLED = True

LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("en", "English")]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

CORS_ALLOWED_ORIGINS = env.cors_origins_list
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "idempotency-key",
    "if-match",
    "x-branch-id",
    "x-mizan-app",
    "x-request-id",
    "x-csrftoken",
]
CORS_EXPOSE_HEADERS = ["etag", "x-request-id", "location"]
CSRF_TRUSTED_ORIGINS = env.cors_origins_list

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if env.is_production_like:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

EMAIL_BACKEND = env.email_backend or (
    "django.core.mail.backends.console.EmailBackend"
    if env.mizan_env == "test"
    else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = env.email_host
EMAIL_PORT = env.email_port
EMAIL_USE_TLS = env.email_use_tls
EMAIL_HOST_USER = env.email_host_user
EMAIL_HOST_PASSWORD = env.email_host_password
DEFAULT_FROM_EMAIL = env.email_from

# Procrastinate (PostgreSQL-backed jobs). Tasks are auto-discovered from every app's tasks.py.
PROCRASTINATE_AUTODISCOVER_MODULE_NAME = "tasks"
PROCRASTINATE_WORKER_DEFAULTS = {
    "fetch_job_polling_interval": 2.0,
    "shutdown_graceful_timeout": 30.0,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": "mizan.platform.logging.JsonFormatter"},
        "console": {"format": "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"},
    },
    "filters": {"context": {"()": "mizan.platform.logging.ContextFilter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if env.log_json else "console",
            "filters": ["context"],
        }
    },
    "root": {"handlers": ["console"], "level": env.log_level},
    "loggers": {
        "django": {"level": "INFO"},
        "django.db.backends": {"level": "WARNING"},
        "procrastinate": {"level": "INFO"},
        "weasyprint": {"level": "ERROR"},
        "fontTools": {"level": "ERROR"},
    },
}

# Platform-level settings (SPEC §18, §27): public origins and signing.
MIZAN_VERIFY_BASE_URL = env.verify_base_url
MIZAN_PORTAL_BASE_URL = env.portal_base_url
MIZAN_SIGNING_BACKEND = env.signing_backend
MIZAN_SIGNING_LOCAL_DIR = BASE_DIR / env.signing_local_dir
MIZAN_TSA_URL = env.tsa_url
MIZAN_STORAGE_BACKEND = env.storage_backend
MIZAN_STORAGE_LOCAL_ROOT = BASE_DIR / env.storage_local_root
MIZAN_JWT_ISSUER = env.jwt_issuer
MIZAN_JWT_ACCESS_TTL = env.jwt_access_ttl_seconds
MIZAN_JWT_REFRESH_TTL = env.jwt_refresh_ttl_seconds
MIZAN_IDEMPOTENCY_TTL_SECONDS = 24 * 3600
