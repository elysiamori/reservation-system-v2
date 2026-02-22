from pydantic import BaseModel, field_validator
from typing import Optional


ALLOWED_TYPES = [
    "image/jpeg","image/jpg","image/png","image/gif","image/webp",
    "application/pdf","application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain","application/zip","application/x-zip-compressed",
]


class AttachmentCreateRequest(BaseModel):
    fileUrl:     str
    fileName:    str
    fileType:    str
    fileSize:    Optional[int] = None
    description: Optional[str] = None

    @field_validator("fileUrl")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(("http://","https://")):
            raise ValueError("fileUrl harus berupa URL valid (http/https)")
        return v

    @field_validator("fileName")
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("fileName tidak boleh kosong")
        return v.strip()

    @field_validator("fileType")
    @classmethod
    def validate_type(cls, v):
        if v not in ALLOWED_TYPES:
            raise ValueError(f"fileType '{v}' tidak didukung. Gunakan: {', '.join(ALLOWED_TYPES)}")
        return v


class ProfilePhotoRequest(BaseModel):
    photoUrl: str

    @field_validator("photoUrl")
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(("http://","https://")):
            raise ValueError("photoUrl harus berupa URL valid")
        return v
