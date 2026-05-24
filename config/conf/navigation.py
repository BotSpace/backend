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
        "separator": True,
        "items": [
            {
                "title": _("Projects"),
                "icon": "folder",
                "link": reverse_lazy("admin:api_projectmodel_changelist"),
            },
            {
                "title": _("Release"),
                "icon": "rocket_launch",
                "link": reverse_lazy("admin:api_relasemodel_changelist"),
            },
            {
                "title": _("Collection"),
                "icon": "collections",
                "link": reverse_lazy("admin:cms_legacy_collectionmodel_changelist"),
            },
        ],
    },
    {
        "title": _("Pricing Plans"),
        "separator": True,
        "items": [
            {
                "title": _("Plans"),
                "icon": "card_membership",
                "link": reverse_lazy("admin:api_planmodel_changelist"),
            },
            {
                "title": _("Subscriptions"),
                "icon": "subscriptions",
                "link": reverse_lazy("admin:api_usersubscription_changelist"),
            },
        ],
    },
    {
        "title": _("Templates"),
        "separator": True,
        "items": [
            {
                "title": _("Templates"),
                "icon": "group",
                "link": reverse_lazy("admin:template_templatemodel_changelist"),
            },
            {
                "title": _("Features"),
                "icon": "group",
                "link": reverse_lazy("admin:template_templatefeaturemodel_changelist"),
            },
            {
                "title": _("Categories"),
                "icon": "group",
                "link": reverse_lazy("admin:template_templatecategorymodel_changelist"),
            },
            {
                "title": _("Orders"),
                "icon": "group",
                "link": reverse_lazy("admin:template_templateordermodel_changelist"),
            },
        ],
    },
]
