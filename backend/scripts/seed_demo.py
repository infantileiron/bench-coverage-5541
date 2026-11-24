import json
from sqlalchemy import func, select

from src.config.database import Base, Session, engine
from src.constants.enums import Role, Status
from src.models.entities import Analysis, Capture, Segment, User
from src.services.business import record
from src.utils.security import password_hash

REGIONS = [('BANK-01','柳渡段','南岸',True,range(1,31),range(13,39)),
           ('BANK-02','石桥段','北岸',True,range(1,18),[1,18,19,20,21,22,23,24]),
           ('BANK-03','船坞段','南岸',False,range(1,13),range(7,16)),
           ('BANK-04','芦廊段','北岸',True,range(1,20),range(8,19))]
CODE = 'NOV21-BENCH'


def seed():
    Base.metadata.create_all(engine)
    with Session() as db:
        for role in Role:
            email = f'{role}@tingyan.demo'
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(email=email, role=role, password_hash=password_hash('BankBench2026!')))
        known = set(db.scalars(select(Segment.code)))
        db.add_all(Segment(code=code, title=title, bank=bank, stable=stable)
                   for code,title,bank,stable,*_ in REGIONS if code not in known)
        db.flush()
        prior = set(db.execute(select(Capture.segment_code, Capture.round_code, Capture.asset_code)
                               .where(Capture.campaign == CODE)).tuples())
        for code, _, _, _, first, second in REGIONS:
            for cycle, sample in (('A',first),('B',second)):
                for number in sample:
                    asset = f'{code}-S{number:03d}'
                    if (code,cycle,asset) not in prior:
                        state = 'unverified' if (code,cycle,number) == ('BANK-04','B',17) else 'verified'
                        db.add(Capture(segment_code=code, campaign=CODE, round_code=cycle, asset_code=asset, state=state))
        db.flush()
        title = '周末早班 · 滨江补巡清单'
        if not db.scalar(select(Analysis).where(Analysis.title == title)):
            owner = db.scalar(select(User).where(User.role == Role.ANALYST))
            params = {'campaign':CODE,'min_overlap':5,'verified_independence':True,
                      'segments':[record(row) for row in db.scalars(select(Segment).order_by(Segment.code))]}
            snapshot = [record(row) for row in db.scalars(select(Capture).where(Capture.campaign == CODE))]
            db.add(Analysis(title=title, status=Status.QUEUED, author_id=owner.id, parameters=params, snapshot=snapshot, result=None))
        db.commit()
        return {model.__tablename__: db.scalar(select(func.count()).select_from(model))
                for model in (User, Segment, Capture, Analysis)}


if __name__ == '__main__':
    print(json.dumps(seed(), sort_keys=True))
