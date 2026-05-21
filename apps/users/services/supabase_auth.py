from apps.users.models import Profile

class SupabaseAuthAdapter:
    """
    Logic for syncing Supabase auth data with local Django profiles.
    """

    @staticmethod
    def sync_profile(user_data: dict):
        profile, created = Profile.objects.update_or_create(
            id=user_data["id"],
            defaults={
                "username": user_data.get("email", "").split('@')[0] if not user_data.get("username") else user_data.get("username"),
            }
        )
        return profile
