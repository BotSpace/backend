import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BlogPostModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                (
                    "slug",
                    models.SlugField(
                        blank=True,
                        help_text="Sarlavhadan avtomatik hosil bo'ladi",
                        max_length=280,
                        unique=True,
                        verbose_name="slug",
                    ),
                ),
                (
                    "excerpt",
                    models.CharField(
                        blank=True,
                        help_text="Qisqa tavsif (ro'yxat kartochkalarida ko'rsatiladi)",
                        max_length=500,
                        verbose_name="excerpt",
                    ),
                ),
                ("content", models.TextField(help_text="Markdown matni", verbose_name="content")),
                (
                    "cover_image",
                    models.URLField(
                        blank=True,
                        help_text="Muqova rasmi havolasi (ixtiyoriy)",
                        max_length=1000,
                        null=True,
                        verbose_name="cover image",
                    ),
                ),
                ("is_published", models.BooleanField(db_index=True, default=False, verbose_name="is published")),
                ("published_at", models.DateTimeField(blank=True, null=True, verbose_name="published at")),
                (
                    "author",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="blog_posts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="author",
                    ),
                ),
            ],
            options={
                "verbose_name": "Blog Post",
                "verbose_name_plural": "Blog Posts",
                "db_table": "blog_post",
                "ordering": ["-published_at", "-created_at"],
            },
        ),
    ]
