from fastapi import HTTPException
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.config.settings import REDIS_URL
from src.constants.enums import Status
from src.models.entities import Analysis, Audit, Segment, Capture

queue = Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
QUEUE = 'bench-coverage:notifications'


def record(obj, exclude=()):
    return {col.key: getattr(obj, col.key) for col in obj.__table__.columns if col.key not in exclude}


def audit(db, user, action, subject):
    db.add(Audit(user_id=user.id, action=action, subject=str(subject)))


def save_input(db, model, data, user):
    if model is Capture:
        if not db.scalar(select(Segment.id).where(Segment.code == data.segment_code)):
            raise HTTPException(422, '请选择有效区段')
        key = f'{data.segment_code}/{data.campaign}/{data.round_code}/{data.asset_code}'
    else:
        key = data.code
    item = model(**data.model_dump())
    db.add(item)
    audit(db, user, 'create', key)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, '区段编号或该轮资产标签已经登记') from exc
    return record(item)


def verify_capture(db, id, user):
    row = db.scalar(select(Capture).where(Capture.id == id).with_for_update())
    if row is None:
        raise HTTPException(404, '找不到待核标签')
    if row.state != 'verified':
        row.state = 'verified'
        audit(db, user, 'verify_capture', f'{row.segment_code}/{row.asset_code}')
        db.commit()
    return record(row)


def submit(db, data, user):
    segments = [record(row) for row in db.scalars(select(Segment).order_by(Segment.code))]
    if not segments:
        raise HTTPException(422, '请先登记巡查区段')
    evidence = db.scalars(select(Capture).where(Capture.campaign == data.campaign).order_by(Capture.id))
    snapshot = [record(row) for row in evidence]
    if not snapshot:
        raise HTTPException(422, '该巡查批次还没有记录')
    parameters = {**data.model_dump(exclude={'title'}), 'segments':segments}
    item = Analysis(title=data.title, status=Status.QUEUED, parameters=parameters,
                    snapshot=snapshot, author_id=user.id, result=None)
    db.add(item)
    db.flush()
    audit(db, user, 'queue', item.id)
    db.commit()
    try:
        queue.lpush(QUEUE, item.id)
    except RedisError:
        pass
    return record(item, ('snapshot',))


def get_analysis(db, id):
    item = db.get(Analysis, id)
    if not item:
        raise HTTPException(404, '找不到补巡单')
    return item


def publish(db, id, note, user):
    item = db.scalar(select(Analysis).where(Analysis.id == id).with_for_update())
    if not item:
        raise HTTPException(404, '找不到补巡单')
    if item.status != Status.COMPLETED:
        raise HTTPException(409, '只有已完成的补巡单可签核')
    item.status = Status.PUBLISHED
    item.note = note
    audit(db, user, 'publish', id)
    db.commit()
    return record(item, ('snapshot',))
