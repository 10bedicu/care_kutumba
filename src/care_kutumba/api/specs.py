"""Pydantic specs for Kutumba API endpoints.

Following Care's pattern of using Pydantic models for request/response validation.
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class BeneficiaryLookupRequest(BaseModel):
    """Request spec for beneficiary lookup."""

    rc_number: str = Field(
        ...,
        min_length=12,
        max_length=12,
        description="Ration Card number (12 digits)",
    )

    @field_validator("rc_number")
    @classmethod
    def validate_rc_number(cls, v: str) -> str:
        """Validate RC number format."""
        v = v.strip()
        if not v.isdigit():
            raise ValueError("RC number must contain only digits")
        return v


class BeneficiaryMember(BaseModel):
    """Spec for a single family member from Kutumba response."""

    health_id: str | None = None
    caste: str | None = None
    education_id: str | None = None
    disability_applicant_no: str | None = None
    name: str
    date_of_birth: str | None = None
    gender: str | None = None
    address: str | None = None
    pincode: str | None = None
    rc_number: str
    rc_type: str | None = None
    relation_name: str | None = None
    mobile_no: str | None = None
    kutumba_id_status: str | None = None
    rch_id: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "BeneficiaryMember":
        """Create a BeneficiaryMember from Kutumba API response data."""
        return cls(
            health_id=data.get("MBR_HEALTH_ID"),
            caste=data.get("MBR_CASTE"),
            education_id=data.get("MBR_EDUCATION_ID"),
            disability_applicant_no=data.get("MBR_Disability_Applicant_No"),
            name=data.get("MEMBER_NAME_ENG", ""),
            date_of_birth=data.get("MBR_DOB"),
            gender=data.get("MBR_GENDER"),
            address=data.get("MBR_ADDRESS"),
            pincode=data.get("MBR_PINCODE"),
            rc_number=data.get("RC_NUMBER", ""),
            rc_type=data.get("RC_TYPE"),
            relation_name=data.get("RELATION_NAME"),
            mobile_no=data.get("MBR_MOBILE_NO"),
            kutumba_id_status=data.get("Kutumba_ID_status"),
            rch_id=data.get("RCH_ID"),
        )


class BeneficiaryLookupResponse(BaseModel):
    """Response spec for beneficiary lookup."""

    success: bool
    status_code: int
    status_text: str
    response_id: str | None = None
    request_id: str | None = None
    request_log_external_id: str | None = None
    members: list[BeneficiaryMember] = []
    error: str | None = None


class PatientLinkRequest(BaseModel):
    """Request spec for linking a patient to a Kutumba lookup result."""

    request_log_external_id: UUID
    selected_member_index: int = Field(..., ge=0)
    patient_external_id: UUID | None = None
    action: Literal["create", "update"]

    @model_validator(mode="after")
    def _patient_required_for_update(self) -> "PatientLinkRequest":
        if self.action == "update" and self.patient_external_id is None:
            raise ValueError("patient_external_id is required when action is 'update'")
        return self
