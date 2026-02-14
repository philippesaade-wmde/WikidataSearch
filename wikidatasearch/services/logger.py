from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import traceback
import time
import os
from hashlib import sha256
import re

"""
MySQL database setup for storing Wikidata labels in all languages.
"""

DB_HOST = os.environ["DB_HOST"]
DB_NAME = os.environ["DB_NAME"]
DB_USER = os.environ["DB_USER"]
DB_PASS = os.environ["DB_PASS"]
DB_PORT = int(os.environ.get("DB_PORT", "3306"))

DATABASE_URL = (
    f"mariadb+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=5,  # Limit the number of open connections
    max_overflow=10,  # Allow extra connections beyond pool_size
    pool_recycle=1800,  # Recycle connections every 30 minutes
    pool_pre_ping=True,
)

Base = declarative_base()
Session = sessionmaker(bind=engine, expire_on_commit=False)

class Logger(Base):
    __tablename__ = 'requests'
    __table_args__ = (
        Index("ix_requests_route_timestamp", "route", "timestamp"),
        Index("ix_requests_status_timestamp", "status", "timestamp"),
        Index("ix_requests_redaction_scan", "is_redacted", "timestamp", "id"),
        {"mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    route = Column(String(128), index=True, nullable=False)
    parameters = Column(JSON, default=dict, nullable=False)
    status = Column(Integer, index=True, nullable=False)
    error = Column(Text)
    response_time = Column(Float, nullable=False)
    is_redacted = Column(Boolean, default=False, index=True, nullable=False)

    # User Agent
    user_agent = Column(String(255))
    user_agent_hash = Column(String(64), index=True, nullable=False)
    on_browser = Column(Boolean, nullable=False, default=False)

    # For queries
    query = Column(Text)
    query_hash = Column(String(64), index=True, nullable=False)
    query_length = Column(Integer, nullable=False, default=0)
    query_words = Column(Integer, nullable=False, default=0)


    @staticmethod
    def add_request(request, status_code, start_time, error=""):
        with Session() as session:
            try:
                # Clean up old logs (older than 90 days)
                Logger.redact_old_requests(90, 1000)

                user_agent = request.headers.get('user-agent', 'unknown')[:255]
                user_agent_hash = sha256(user_agent.encode('utf-8')).hexdigest()
                on_browser = 'Mozilla' in user_agent

                query = request.query_params.get('query', '')
                query_hash = sha256(query.encode('utf-8')).hexdigest()
                query_length = len(query)
                query_words = len(re.findall(r'\w+', query))

                parameters = dict(request.query_params)
                parameters.pop('query', None)

                # Add new log entry
                log_entry = Logger(
                    route=request.url.path[:128],
                    user_agent=user_agent,
                    user_agent_hash=user_agent_hash,
                    on_browser=on_browser,
                    parameters=parameters,
                    query=query,
                    query_hash=query_hash,
                    query_length=query_length,
                    query_words=query_words,
                    status=status_code,
                    error=error,
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
                    row.user_agent = ""
                    row.query = ""
                    row.is_redacted = True
                    changed = True

                if changed:
                    session.commit()

            except Exception as e:
                session.rollback()
                traceback.print_exc()

class Feedback(Base):
    __tablename__ = 'feedback'
    __table_args__ = (
        Index("ix_feedback_qid", "qid"),
        {"mysql_charset": "utf8mb4"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(512))
    qid = Column(String(32))
    sentiment = Column(String(32))
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
