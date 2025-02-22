"""
Register models for admin panel management
"""
from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.translation import ngettext
from feeds import models
from feeds.feed_updates import update_feed


class SourceAdmin(admin.ModelAdmin):
    """
    Adds link to a sources entries to the admin panel
    """
    list_display = ["name", "entries_link"]
    readonly_fields = ('entries_link',)
    actions = ['update_feeds']

    @admin.action(description="Refresh Feeds")
    def update_feeds(self, request, queryset):
        """This admin action will update the selected sources"""
        for source in queryset:
            update_feed(source, no_cache=True)

        n_updated = len(queryset)

        self.message_user(
            request,
            ngettext(
                "%d feed was updated.",
                "%d feeds were updated.",
                n_updated,
            )
            % n_updated,
            messages.SUCCESS,
        )

    def entries_link(self, source: models.Source) -> str:
        """
        Returns an html link string to the given sources entries
        """
        if source.id is None:
            return ''
        qs = source.entries.all()
        return mark_safe(
            '<a href="%s?source__id=%i" target="_blank">%i Posts</a>' % (
                reverse('admin:feeds_entry_changelist'), source.id, qs.count()
            )
        )
    entries_link.short_description = 'entries'



class EntryAdmin(admin.ModelAdmin):
    """
    Adds a link to a entry's enclosures to the admin panel
    """

    raw_id_fields = ('source',)
    list_display = ('title', 'enclosures_link', 'source', 'created', 'guid', 'author')
    search_fields = ('title',)

    readonly_fields = (
        'enclosures_link',
    )

    def enclosures_link(self, entry: models.Entry) -> str:
        """
        Returns an html link to the given entry's enclosures
        """
        if entry.id is None:
            return ''
        qs = entry.enclosures.all()
        return mark_safe(
            '<a href="%s?entry__id=%i" target="_blank">%i Enclosures</a>' % (
                reverse('admin:feeds_enclosure_changelist'), entry.id, qs.count()
            )
        )
    enclosures_link.short_description = 'enclosures'



class EnclosureAdmin(admin.ModelAdmin):
    """
    Admin panel for enclosures
    """

    raw_id_fields = ('entry',)
    list_display = ('href', 'type')


admin.site.register(models.Source, SourceAdmin)
admin.site.register(models.Entry, EntryAdmin)
admin.site.register(models.Enclosure, EnclosureAdmin)
admin.site.register(models.WebProxy)
