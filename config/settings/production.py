"""Production settings — used on Render."""

from .base import *
from .base import env

DEBUG = False

ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# Nothing on this domain reads the CSRF cookie via JS (the frontend is a
# separate origin calling the JSON API, not a page served by this app).
CSRF_COOKIE_HTTPONLY = True

# Don't serve the interactive HTML API browser in production — same
# permissions apply either way, but it's needless surface for a JSON API.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

# Serve collected static files (incl. the admin) through WhiteNoise.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# Uploaded media (equipment photos, etc.). Render's disk is wiped on every
# deploy and nothing serves /media/ with DEBUG off, so production uploads
# must go to an S3-compatible bucket (AWS S3, Cloudflare R2, Backblaze B2...).
# Without a bucket configured we fall back to the local filesystem, which is
# only suitable for a throwaway demo.
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")

if AWS_STORAGE_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    # Public host for media URLs, e.g. a CDN or the bucket's public domain.
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=False)
    AWS_S3_FILE_OVERWRITE = False
    DEFAULT_FILE_STORAGE_BACKEND = "storages.backends.s3.S3Storage"
else:
    DEFAULT_FILE_STORAGE_BACKEND = "django.core.files.storage.FileSystemStorage"

STORAGES = {
    "default": {
        "BACKEND": DEFAULT_FILE_STORAGE_BACKEND,
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Security — assumes TLS is terminated by the platform proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
