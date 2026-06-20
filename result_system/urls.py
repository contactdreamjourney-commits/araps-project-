from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from students.views import home_redirect, ARAPSLoginView, custom_logout

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_redirect, name='home'),
    path('login/', ARAPSLoginView.as_view(), name='login'),
    path('logout/', custom_logout, name='logout'),
    path('', include('students.urls')),
    path('teacher/', include('teachers.urls')),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])