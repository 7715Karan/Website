from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('option_chain.urls')),  # Include app URLs
    # Add other URL patterns as needed
]