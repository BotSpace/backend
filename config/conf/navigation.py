from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

PAGES = [
    {
        "seperator": False,
        "items": [
            {
                "title": _("Home page"),
                "icon": "home",
                "link": reverse_lazy("admin:index"),
            }
        ],
    },
    {
        "title": _("Auth"),
        "separator": True,  # Top border
        "items": [
            {
                "title": _("Users"),
                "icon": "group",
                "link": reverse_lazy("admin:accounts_user_changelist"),
            },
            {
                "title": _("Group"),
                "icon": "group",
                "link": reverse_lazy("admin:auth_group_changelist"),
            },
        ],
    },
    {
        "title": _("Dashboard"),
        "separator": True,  # Top border
        "items": [
            {
                "title": _("Projects"),
                "icon": "group",
                "link": reverse_lazy("admin:api_projectmodel_changelist"),
            },
            {
                "title": _("Release"),
                "icon": "group",
                "link": reverse_lazy("admin:api_relasemodel_changelist"),
            },
            {
                "title": _("Collection"),
                "icon": "group",
                "link": reverse_lazy("admin:cms_collectionmodel_changelist"),
            },
        ],
    },
]
