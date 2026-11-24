from typing import Literal
from pydantic import BaseModel, Field, field_validator

ASSET_PATTERN = r'^[A-Z0-9-]{2,40}$'


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


class SamplingInput(CleanInput):
    title: str = Field(min_length=2, max_length=100)
    campaign: str = Field(pattern=r'^[A-Z0-9-]{2,32}$')
    sample_sizes: dict[str, int] = Field(min_length=1)
    confidence: float = Field(ge=0.8, le=0.99, default=0.9)
    seed: int = Field(ge=0, le=2**32 - 1)

    @field_validator('sample_sizes')
    @classmethod
    def _sizes_positive(cls, value):
        if any(size < 1 for size in value.values()):
            raise ValueError('每个岸线的抽签数量至少为 1')
        return value


class RerunSampling(CleanInput):
    sample_sizes: dict[str, int] = Field(min_length=1)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)

    @field_validator('sample_sizes')
    @classmethod
    def _sizes_positive(cls, value):
        if any(size < 1 for size in value.values()):
            raise ValueError('每个岸线的抽签数量至少为 1')
        return value


class RecountInput(CleanInput):
    total_found: int = Field(ge=0)
    asset_codes: list[str] = Field(min_length=1)
    reason: str = Field(default='', max_length=400)
    reporter: str = Field(min_length=2, max_length=120)

    @field_validator('asset_codes')
    @classmethod
    def _asset_format(cls, value):
        import re
        cleaned = []
        for code in value:
            code = code.strip().upper()
            if not re.match(ASSET_PATTERN, code):
                raise ValueError(f'资产编号格式不正确：{code}')
            cleaned.append(code)
        if len(set(cleaned)) != len(cleaned):
            raise ValueError('回传编号存在重复，请先在现场清单内去重')
        return cleaned


class BlockInput(CleanInput):
    reason: str = Field(min_length=3, max_length=400)
    reporter: str = Field(min_length=2, max_length=120)
