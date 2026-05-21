# apps/users/services/supabase_auth.py

class SupabaseAuthAdapter:
    """
    Interface logique vers auth.users (Supabase)
    """

    @staticmethod
    def get_user(user_id: str):
        # appel API Supabase ou JWT decode
        pass

    @staticmethod
    def sync_profile(user_data: dict):
        from apps.users.models import Profile

        profile, created = Profile.objects.update_or_create(
            id=user_data["id"],
            defaults={
                "username": user_data.get("email"),
            }
        )
        return profile