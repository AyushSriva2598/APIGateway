import hashlib
import secrets
import uuid

from django.db import models


class Tier(models.Model):
    ALGORITHM_CHOICES = [
        ('token_bucket', 'Token Bucket'),
        ('fixed_window', 'Fixed Window'),
        ('sliding_window', 'Sliding Window Log'),
    ]

    name = models.CharField(max_length=50, unique=True)  # 'free', 'pro', 'enterprise'
    algorithm = models.CharField(max_length=20, choices=ALGORITHM_CHOICES)

    # Not every algorithm uses every field — token_bucket needs capacity +
    # refill_rate, fixed_window/sliding_window need limit + window_seconds.
    # Nullable rather than splitting into per-algorithm tables; simplicity
    # over strict normalization at this stage of the project.
    capacity = models.PositiveIntegerField(null=True, blank=True)
    refill_rate = models.FloatField(null=True, blank=True)  # tokens per second
    limit = models.PositiveIntegerField(null=True, blank=True)
    window_seconds = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def to_algorithm_config(self) -> dict:
        """Shape matches ratelimiter.config's existing dict format exactly,
        so the factory in ratelimiter/algorithms/factory.py can consume
        this without changes once it's wired in."""
        config = {'algorithm': self.algorithm}
        if self.algorithm == 'token_bucket':
            config.update(capacity=self.capacity, refill_rate=self.refill_rate)
        else:
            config.update(limit=self.limit, window_seconds=self.window_seconds)
        return config


class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Never store the raw key — only its hash. key_prefix is what's shown
    # in the admin/UI so a human can identify a key without ever seeing
    # the full secret again after creation.
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)  # sha256 hex digest
    key_prefix = models.CharField(max_length=12, db_index=True)

    owner = models.CharField(max_length=255)  # placeholder — no User model tie-in yet
    tier = models.ForeignKey(Tier, on_delete=models.PROTECT, related_name='api_keys')

    is_active = models.BooleanField(default=True)

    # Per-key exception to the tier's default limit — null means "use the
    # tier's config as-is." Same shape as Tier's fields, deliberately, so
    # a resolver can do rate_limit_override or tier.to_algorithm_config().
    rate_limit_override = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['key_hash'])]

    def __str__(self):
        return f'{self.key_prefix}... ({self.owner})'

    @staticmethod
    def generate_key() -> tuple[str, str, str]:
        """Returns (raw_key, key_hash, key_prefix). raw_key is shown to the
        user exactly once at creation time — it is never stored or
        retrievable again after this call returns."""
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        return raw_key, key_hash, key_prefix

    def resolve_algorithm_config(self) -> dict:
        if self.rate_limit_override:
            return self.rate_limit_override
        return self.tier.to_algorithm_config()