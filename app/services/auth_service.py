from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self):
        self.repo = UserRepository()

    def get_user(self, user_id: int):
        return self.repo.get_user(user_id)

    def enforce_scope(self, user, requested_huilerie: str | None) -> str | None:
        if not user:
            return requested_huilerie
        if user["role"] == "direction":
            return requested_huilerie
        if requested_huilerie and user["huilerie_nom"] and requested_huilerie.lower() != user["huilerie_nom"].lower():
            return user["huilerie_nom"]
        return requested_huilerie or user["huilerie_nom"]
