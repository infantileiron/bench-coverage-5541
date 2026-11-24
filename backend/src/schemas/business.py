from typing import Literal
from pydantic import BaseModel, Field


class CleanInput(BaseModel, str_strip_whitespace=True, extra='forbid'):
    pass


class Login(CleanInput):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class SegmentInput(CleanInput):
    code: str = Field(pattern=r'^[A-Z0-9-]{2,32}$')
    title: str = Field(min_length=2, max_length=100)
    bank: str = Field(min_length=2, max_length=40)
    stable: bool


class CaptureInput(CleanInput):
    segment_code: str = Field(pattern=r'^[A-Z0-9-]{2,32}$')
    campaign: str = Field(pattern=r'^[A-Z0-9-]{2,32}$')
    round_code: Literal['A', 'B']
    asset_code: str = Field(pattern=r'^[A-Z0-9-]{2,40}$')
    state: Literal['verified', 'unverified']


class AnalysisInput(CleanInput):
    title: str = Field(min_length=2, max_length=100)
    campaign: str = Field(pattern=r'^[A-Z0-9-]{2,32}$')
    min_overlap: int = Field(ge=3, le=200, default=5)
    verified_independence: bool


class Publication(CleanInput):
    note: str = Field(min_length=3, max_length=400)
