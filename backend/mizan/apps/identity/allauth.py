from __future__ import annotations

from typing import Any

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):  # type: ignore[misc]
    """No self-signup: users are created by staff or by the tenant administrator."""

    def is_open_for_signup(self, request: Any) -> bool:
        return False
