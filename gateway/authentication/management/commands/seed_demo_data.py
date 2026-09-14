"""
Auto-seeds tiers + API keys for the live demo.
Idempotent — safe to run on every instance boot.

Usage: python manage.py seed_demo_data
Keys are printed to stdout (captured in /var/log/user-data.log).
"""
from django.core.management.base import BaseCommand
from authentication.models import Tier, APIKey


class Command(BaseCommand):
    help = "Seed demo tiers and API keys for the presentation"

    def handle(self, *args, **options):
        self.stdout.write("\n── Seeding Demo Data ──\n")

        # ── Tiers ──
        free_tier, _ = Tier.objects.get_or_create(
            name="free",
            defaults=dict(algorithm="token_bucket", capacity=10, refill_rate=10 / 60),
        )
        pro_tier, _ = Tier.objects.get_or_create(
            name="pro",
            defaults=dict(algorithm="sliding_window", limit=100, window_seconds=60),
        )
        ent_tier, _ = Tier.objects.get_or_create(
            name="enterprise",
            defaults=dict(algorithm="fixed_window", limit=1000, window_seconds=60),
        )
        self.stdout.write(f"  Tiers: free, pro, enterprise ✓")

        # ── API Keys ──
        for tier, owner in [
            (free_tier, "demo-free"),
            (pro_tier, "demo-pro"),
            (ent_tier, "demo-enterprise"),
        ]:
            if not APIKey.objects.filter(owner=owner).exists():
                raw_key, key_hash, key_prefix = APIKey.generate_key()
                APIKey.objects.create(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    owner=owner,
                    tier=tier,
                )
                self.stdout.write(self.style.SUCCESS(
                    f"  ✅ {owner:20s} → {raw_key}"
                ))
            else:
                existing = APIKey.objects.get(owner=owner)
                self.stdout.write(f"  ⏭  {owner:20s} → already exists ({existing.key_prefix}...)")

        self.stdout.write(self.style.SUCCESS("\n  Demo data ready!\n"))
