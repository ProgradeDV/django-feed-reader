"""
Register models for admin panel management
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

# Register your models here.
from feeds import models


class SourceAdmin(admin.ModelAdmin):
    """
    Adds link to a sources posts to the admin panel
    """

    readonly_fields = ('posts_link',)

    def posts_link(self, source: models.Source) -> str:
        """
        Returns an html link string to the given sources posts
        """
        if source.id is None:
            return ''
        qs = source.posts.all()
        return mark_safe(
            '<a href="%s?source__id=%i" target="_blank">%i Posts</a>' % (
                reverse('admin:feeds_post_changelist'), source.id, qs.count()
            )
        )
    posts_link.short_description = 'posts'



class PostAdmin(admin.ModelAdmin):
    """
    Adds a link to a posts enclosures to the admin panel
    """

    raw_id_fields = ('source',)
    list_display = ('title', 'source', 'created', 'guid', 'author')
    search_fields = ('title',)

    readonly_fields = (
        'enclosures_link',
    )

    def enclosures_link(self, post: models.Post) -> str:
        """
        Returns an html link to the given posts enclosures
        """
        if post.id is None:
            return ''
        qs = post.enclosures.all()
        return mark_safe(
            '<a href="%s?post__id=%i" target="_blank">%i Enclosures</a>' % (
                reverse('admin:feeds_enclosure_changelist'), post.id, qs.count()
            )
        )
    enclosures_link.short_description = 'enclosures'



class EnclosureAdmin(admin.ModelAdmin):
    """
    Admin panel for enclosures
    """

    raw_id_fields = ('post',)
    list_display = ('href', 'type')


admin.site.register(models.Source, SourceAdmin)
admin.site.register(models.Post, PostAdmin)
admin.site.register(models.Enclosure, EnclosureAdmin)
admin.site.register(models.WebProxy)
