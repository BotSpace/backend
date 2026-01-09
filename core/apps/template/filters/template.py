from django.db.models import Q
from django_filters import rest_framework as filters

from core.apps.template.models import TemplateModel


class TemplateFilter(filters.FilterSet):
    search = filters.CharFilter(method="filter_search")
    price = filters.RangeFilter(field_name="original_price")

    class Meta:
        model = TemplateModel
        fields = [
            "categories",
            "features",
        ]

    def filter_search(self, queryset, name, value):
        """
        AI-friendly smart search
        Searches in: name, description, categories, features
        Uses OR logic - finds templates matching ANY keyword
        """
        if not value:
            return queryset
        
        # Split search value into keywords
        keywords = value.lower().split()
        
        # Build OR query for all keywords
        # Template matches if it contains ANY of the keywords
        query = Q()
        for keyword in keywords:
            keyword_query = (
                Q(name__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(short_description__icontains=keyword) |
                Q(categories__name__icontains=keyword) |
                Q(features__name__icontains=keyword)
            )
            query |= keyword_query  # Changed from &= to |= (AND to OR)
        
        # Return distinct results (to avoid duplicates from many-to-many joins)
        return queryset.filter(query).distinct()

