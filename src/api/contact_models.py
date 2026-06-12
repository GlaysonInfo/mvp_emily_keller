from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactSubmission(BaseModel):
    contact_type: str = Field(default="Contato", min_length=3, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    company: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=40)
    subject: str = Field(default="", max_length=180)
    message: str = Field(min_length=5, max_length=4000)
    consent: bool
    website: str = Field(default="", max_length=200)

    @field_validator("contact_type", "name", "email", "company", "phone", "subject", "message", "website")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("Informe um e-mail válido.")
        return value.lower()


class ContactSubmissionResponse(BaseModel):
    ok: bool
    message: str
    request_id: str


class ContactHealthResponse(BaseModel):
    ok: bool
    service: str
    region: str
    delivery_configured: bool
