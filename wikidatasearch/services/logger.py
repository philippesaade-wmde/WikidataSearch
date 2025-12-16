from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import traceback
import json
import time
import os
from hashlib import sha256
import re

TOOL_DATA_DIR = os.environ.get("TOOL_DATA_DIR", "./data")
DB_URL = os.path.join(TOOL_DATA_DIR, 'request_logs.db')
SQLA_URL = f"sqlite:///{DB_URL}"
Base = declarative_base()

engine = create_engine(SQLA_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Logger(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    route = Column(String)
    user_agent = Column(String)
    parameters = Column(String)
    status = Column(Integer)
    response = Column(String)
    response_time = Column(Float)
    is_redacted = Column(Boolean)

    @staticmethod
    def add_request(request, response, status_code, start_time):
        with Session() as session:
            try:
                # Clean up old logs (older than 90 days)
                Logger.redact_old_requests(90, 1000)

                # Add new log entry
                log_entry = Logger(
                    route=request.url.path,
                    user_agent=request.headers.get('user-agent', 'unknown')[:255],
                    parameters=json.dumps(
                        dict(request.query_params),
                        separators=(',', ':')
                    ),
                    status=status_code,
                    response=json.dumps(
                        response,
                        separators=(',', ':')
                    ),
                    response_time=time.time() - start_time,
                    is_redacted=False
                )
                session.add(log_entry)
                session.commit()
            except Exception as e:
                session.rollback()
                traceback.print_exc()

    @staticmethod
    def redact_old_requests(days: int=90, batch_size: int=1000):
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        with Session() as session:
            try:
                old_requests = (
                    session.query(Logger)
                    .filter(Logger.timestamp < cutoff_date)
                    .filter((Logger.is_redacted.is_(None)) | (Logger.is_redacted == False))
                    .order_by(Logger.id.asc())
                    .yield_per(batch_size)
                )

                changed = False
                for row in old_requests:
                    raw_params = row.parameters or "{}"
                    try:
                        params = json.loads(raw_params)
                    except:
                        params = {}

                    params['query_len'] = len(params.get('query', ''))

                    _WORD_RE = re.compile(r"\w+", re.UNICODE)
                    params['query_words'] = len(_WORD_RE.findall(params.get('query', '')))

                    params['query'] = sha256(params.get('query', '').encode('utf-8')).hexdigest()
                    row.parameters = json.dumps(
                        params,
                        separators=(',', ':')
                    )

                    row.user_agent = sha256(row.user_agent.encode('utf-8')).hexdigest()

                    row.is_redacted = True
                    changed = True

                if changed:
                    session.commit()

            except Exception as e:
                session.rollback()
                traceback.print_exc()

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String)
    qid = Column(String)
    sentiment = Column(String)
    index = Column(Integer)

    @staticmethod
    def add_feedback(query, qid, sentiment, index):
        with Session() as session:
            try:
                # Add new feedback
                feedback_entry = Feedback(
                    query=query,
                    qid=qid,
                    sentiment=sentiment,
                    index=index,
                )
                session.add(feedback_entry)
                session.commit()
            except Exception as e:
                session.rollback()
                traceback.print_exc()

Base.metadata.create_all(bind=engine)