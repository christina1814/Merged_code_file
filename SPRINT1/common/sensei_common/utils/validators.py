"""
Validation helpers shared by VKIS & Authoring.

These are light helpers – your app services still own business rules.
"""

from __future__ import annotations

from typing import Iterable, Set


VALID_SENSITIVITIES: Set[str] = {"Public", "Internal", "Confidential"}


def validate_sensitivity(value: str) -> None:
    if value not in VALID_SENSITIVITIES:
        from sensei_common.utils.exceptions import ValidationError
        raise ValidationError("KA-API-0002", f"Invalid sensitivity: {value}")


def validate_required_fields(payload: dict, required: Iterable[str]) -> None:
    missing = [k for k in required if k not in payload or payload[k] in (None, "", [])]
    if missing:
        from sensei_common.utils.exceptions import ValidationError
        raise ValidationError("KA-API-0002", f"Missing required fields: {', '.join(missing)}")
