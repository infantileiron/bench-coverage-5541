from enum import StrEnum


class Role(StrEnum):
    MANAGER = 'manager'
    ANALYST = 'analyst'
    VIEWER = 'viewer'


class Status(StrEnum):
    QUEUED = 'queued'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PUBLISHED = 'published'


class SamplingStatus(StrEnum):
    DRAFT = 'draft'
    ESTIMATED = 'estimated'
    INCONCLUSIVE = 'inconclusive'


class RecountState(StrEnum):
    PENDING = 'pending'
    COUNTED = 'counted'
    BLOCKED = 'blocked'
    SUSPENDED = 'suspended'
