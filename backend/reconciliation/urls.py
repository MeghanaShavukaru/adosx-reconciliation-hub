from django.urls import path

from .views import import_summary, organizations, locations, discrepancies

urlpatterns = [
    path("organizations/", organizations, name="organizations"),
    path("locations/", locations, name="locations"),
    path("discrepancies/", discrepancies, name="discrepancies"),
    path("import-summary/", import_summary, name="import-summary"),
]
