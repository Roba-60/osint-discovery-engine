from sqlalchemy import create_engine, Column, String, Float, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///./osint_jobs.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class JobModel(Base):
    __tablename__ = "jobs"

    job_id = Column(String, primary_key=True, index=True)
    seed_type = Column(String, nullable=False)
    seed_value = Column(String, nullable=False)
    status = Column(String, default="processing")
    discovered_nodes = Column(JSON, default=[])
    graph_network = Column(JSON, default={})
    confidence_score = Column(Float, default=0.0)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
