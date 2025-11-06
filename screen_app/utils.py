from django.conf import settings
from screen_app.models import AssemblySession, BOMItem, Product, Station


def environment_callback(request):
    """Returns environment info for Unfold header"""
    return "Production" if not settings.DEBUG else "Development"

def dashboard_callback(request):
    """Returns dashboard data for Unfold"""
    return {
        "cards": [
            {
                "title": "Active Stations",
                "value": Station.objects.filter(current_product__isnull=False).count(),
                "icon": "desktop_windows",
                "color": "primary",
            },
            {
                "title": "BOM Items",
                "value": BOMItem.objects.filter(is_active=True).count(),
                "icon": "list_alt",
                "color": "success",
            },
            {
                "title": "Active Sessions",
                "value": AssemblySession.objects.filter(completed=False).count(),
                "icon": "play_circle",
                "color": "warning",
            },
            {
                "title": "Products",
                "value": Product.objects.count(),
                "icon": "category",
                "color": "info",
            },
        ],
        "charts": [
            {
                "title": "Assembly Progress",
                "type": "doughnut",
                "data": {
                    "labels": ["Completed", "In Progress", "Pending"],
                    "datasets": [{
                        "data": [65, 25, 10],
                        "backgroundColor": ["#10B981", "#F59E0B", "#EF4444"],
                    }],
                },
            },
        ],
    }
