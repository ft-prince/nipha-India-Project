"""
URL configuration for fcc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from screen_app import views
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

# Customize Django Admin Headers
admin.site.site_header = "NIPHA India Admin Dashboard"
admin.site.site_title = "NIPHA India Admin"
admin.site.index_title = "BRG Assembly 40K Management"

urlpatterns = [
    path('admin/', admin.site.urls),
   path('station/', include('screen_app.urls')),
   path('', views.workflow_guide, name='Reference'),
   path('supervisor-dashboard.html', views.supervisor_dashboard, name='Supervisor'),
   path('workflow-guide.html', views.workflow_guide, name='Supervisor'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)