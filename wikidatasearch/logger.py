from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import json
import time
import os

TOOL_DATA_DIR = os.environ.get("TOOL_DATA_DIR", "./data")
DATABASE_URL = os.path.join(TOOL_DATA_DIR, 'request_logs.db')
DATABASE_URL = f"sqlite:///{DATABASE_URL}"
Base = declarative_base()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

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

    @staticmethod
    def add_request(request, response, status_code, start_time):
        with Session() as session:
            # Clean up old logs (older than 90 days)
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            session.query(Logger).filter(Logger.timestamp < cutoff_date).delete()

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
                response_time=time.time() - start_time
            )
            session.add(log_entry)
            session.commit()

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
            # Add new feedback
            feedback_entry = Feedback(
                query=query,
                qid=qid,
                sentiment=sentiment,
                index=index,
            )
            session.add(feedback_entry)
            session.commit()

Base.metadata.create_all(bind=engine)