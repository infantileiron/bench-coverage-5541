from fastapi import APIRouter, Depends
from sqlalchemy import select

from src.config.database import get_db
from src.controllers.auth import current, login, manager, writable
from src.controllers.export import export
from src.models.entities import Analysis, Audit, Segment, Capture
from src.schemas.business import (AnalysisInput, BlockInput, CaptureInput, Login, Publication,
                                  RecountInput, RerunSampling, SamplingInput, SegmentInput)
from src.services import business as svc
from src.services import audit_sampling as sampling
from src.services.coverage import capture_counts, group_captures

router = APIRouter(prefix='/api')


@router.post('/auth/login')
def sign_in(data: Login, db=Depends(get_db)):
    return login(data, db)


@router.get('/auth/me')
def me(user=Depends(current)):
    return {'email': user.email, 'role': user.role}


@router.get('/segments')
def segments(db=Depends(get_db), user=Depends(current)):
    return [svc.record(item) for item in db.scalars(select(Segment).order_by(Segment.code))]


@router.post('/segments', status_code=201)
def create_segment(data: SegmentInput, db=Depends(get_db), user=Depends(writable)):
    return svc.save_input(db, Segment, data, user)


@router.get('/captures')
def captures(campaign: str | None = None, segment_code: str | None = None, db=Depends(get_db), user=Depends(current)):
    query = select(Capture).order_by(Capture.id.desc())
    if campaign:
        query = query.where(Capture.campaign == campaign)
    if segment_code:
        query = query.where(Capture.segment_code == segment_code)
    return [svc.record(item) for item in db.scalars(query)]


@router.get('/captures/summary')
def summary(campaign: str, segment_code: str, db=Depends(get_db), user=Depends(current)):
    query = select(Capture).where(Capture.campaign == campaign, Capture.segment_code == segment_code)
    captures = (svc.record(item) for item in db.scalars(query))
    return capture_counts(group_captures(captures)[segment_code])


@router.post('/captures', status_code=201)
def create_capture(data: CaptureInput, db=Depends(get_db), user=Depends(writable)):
    return svc.save_input(db, Capture, data, user)


@router.post('/captures/{id}/verify')
def verify_capture(id: int, db=Depends(get_db), user=Depends(writable)):
    return svc.verify_capture(db, id, user)


@router.get('/analyses')
def analyses(db=Depends(get_db), user=Depends(current)):
    return [svc.record(item, ('snapshot', 'result')) for item in db.scalars(select(Analysis).order_by(Analysis.id.desc()))]


@router.post('/analyses', status_code=202)
def enqueue(data: AnalysisInput, db=Depends(get_db), user=Depends(writable)):
    return svc.submit(db, data, user)


@router.get('/analyses/{id}')
def analysis(id: int, db=Depends(get_db), user=Depends(current)):
    return svc.record(svc.get_analysis(db, id), ('snapshot',))


@router.get('/analyses/{id}/export')
def download(id: int, db=Depends(get_db), user=Depends(current)):
    return export(svc.get_analysis(db, id))


@router.post('/analyses/{id}/publish')
def publish(id: int, data: Publication, db=Depends(get_db), user=Depends(manager)):
    return svc.publish(db, id, data.note, user)


@router.get('/sampling/plans')
def sampling_plans(db=Depends(get_db), user=Depends(current)):
    return sampling.list_plans(db)


@router.post('/sampling/plans', status_code=201)
def create_sampling(data: SamplingInput, db=Depends(get_db), user=Depends(writable)):
    return sampling.create_plan(db, data, user)


@router.get('/sampling/plans/{plan_id}')
def sampling_plan(plan_id: int, db=Depends(get_db), user=Depends(current)):
    return svc.record(sampling.get_plan(db, plan_id))


@router.post('/sampling/plans/{plan_id}/rerun')
def rerun_sampling(plan_id: int, data: RerunSampling, db=Depends(get_db), user=Depends(writable)):
    return svc.record(sampling.rerun(db, plan_id, data, user))


@router.post('/sampling/plans/{plan_id}/segments/{segment_code}/recount')
def submit_recount(plan_id: int, segment_code: str, data: RecountInput,
                   db=Depends(get_db), user=Depends(writable)):
    return svc.record(sampling.submit_return(db, plan_id, segment_code, data, user))


@router.post('/sampling/plans/{plan_id}/segments/{segment_code}/blocked')
def mark_blocked(plan_id: int, segment_code: str, data: BlockInput,
                 db=Depends(get_db), user=Depends(writable)):
    return svc.record(sampling.mark_blocked(db, plan_id, segment_code, data, user))


@router.get('/audits')
def audit_log(db=Depends(get_db), user=Depends(manager)):
    return [svc.record(item) for item in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(100))]
