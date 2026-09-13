from django.contrib import admin, messages
from .models import APIKey, Tier


@admin.register(Tier)
class TierAdmin(admin.ModelAdmin):
    list_display = ('name', 'algorithm', 'capacity', 'refill_rate', 'limit', 'window_seconds')
    search_fields = ('name',)


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('key_prefix', 'owner', 'tier', 'is_active', 'created_at', 'last_used_at')
    list_filter = ('is_active', 'tier')
    search_fields = ('key_prefix', 'owner')
    readonly_fields = ('id', 'key_hash', 'key_prefix', 'created_at', 'last_used_at')

    actions = ['revoke_keys']

    fields = ('owner', 'tier', 'is_active', 'rate_limit_override',
              'key_prefix', 'key_hash', 'created_at', 'last_used_at')

    def save_model(self, request, obj, form, change):
        if not change:
            # new key being created via admin — generate it here, not left
            # to the caller, since the raw key must never be typed in manually
            raw_key, key_hash, key_prefix = APIKey.generate_key()
            obj.key_hash = key_hash
            obj.key_prefix = key_prefix
            super().save_model(request, obj, form, change)

            # shown exactly once — this is the only moment the raw key
            # exists anywhere outside the client that will use it
            messages.warning(
                request,
                f'API key created. Copy it now — it will not be shown again: {raw_key}'
            )
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description='Revoke selected API keys')
    def revoke_keys(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} key(s) revoked.', level=messages.SUCCESS)