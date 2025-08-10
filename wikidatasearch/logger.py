from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import time
import os

TOOL_DATA_DIR = os.environ.get("TOOL_DATA_DIR", "./")
DATABASE_URL = os.path.join(TOOL_DATA_DIR, 'sql_logs.db')
DATABASE_URL = f"sqlite:///{DATABASE_URL}"
Base = declarative_base()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)

class Logger(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip = Column(String)
    route = Column(String)
    parameters = Column(String)
    status = Column(Integer)
    response = Column(String)
    response_time = Column(Float)

    @staticmethod
    def add_request(request, response, status_code, start_time):
        with Session() as session:
            log_entry = Logger(
                ip=request.client.host,
                route=request.url.path,
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

Base.metadata.create_all(bind=engine)