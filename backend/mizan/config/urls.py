from django.contrib import admin
from django.urls import include, path

from mizan.config.api import api
from mizan.platform.health import health, ready

urlpatterns = [
    path("health", health, name="health"),
    path("ready", ready, name="ready"),
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls),
    path("_allauth/", include("allauth.headless.urls")),
]
