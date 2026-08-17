from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import uuid
import asyncio
import json
from app.scrapers import search_public_username
from app.graph import IdentityGraphBuilder
from app.database import SessionLocal, JobModel, get_db

app = FastAPI(title="Ad-Hoc OSINT Discovery Engine")

class SeedInput(BaseModel):
    seed_type: str
    seed_value: str

class DiscoveryJob(BaseModel):
    job_id: str
    status: str
    discovered_nodes: List[Dict[str, Any]] = []
    graph_network: Dict[str, Any] = {}
    confidence_score: float = 0.0

    class Config:
        from_attributes = True

async def execute_discovery(job_id: str, seed_type: str, seed_value: str):
    results = []
    if seed_type == "username":
        results = await search_public_username(seed_value)
    
    graph_builder = IdentityGraphBuilder()
    graph_summary = graph_builder.build_identity_network(seed_type, seed_value, results)

    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job:
            job.discovered_nodes = results
            job.graph_network = graph_summary
            job.confidence_score = min(len(results) * 0.3, 1.0)
            job.status = "completed"
            db.commit()
    finally:
        db.close()

def run_async_job(job_id: str, seed_type: str, seed_value: str):
    asyncio.run(execute_discovery(job_id, seed_type, seed_value))

@app.post("/api/v1/search", response_model=DiscoveryJob)
async def start_search(seed: SeedInput, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if seed.seed_type not in ["username", "email", "image_url"]:
        raise HTTPException(status_code=400, detail="Invalid seed type")
    
    job_id = str(uuid.uuid4())
    db_job = JobModel(
        job_id=job_id,
        seed_type=seed.seed_type,
        seed_value=seed.seed_value,
        status="processing"
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)

    background_tasks.add_task(run_async_job, job_id, seed.seed_type, seed.seed_value)
    return db_job

@app.get("/api/v1/results/{job_id}", response_model=DiscoveryJob)
async def get_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/view/{job_id}", response_class=HTMLResponse)
async def view_graph(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    graph_data_json = json.dumps(job.graph_network.get("graph_data", {}))

    html_content = f"""
    
    
    
        OSINT Identity Graph - {job_id}
        
        
    
    
        
            OSINT Graph Visualizer
            Job ID: {job_id} | Seed: {job.seed_value} ({job.seed_type}) | Status: {job.status}
        
        

        
    
    
    """
    return HTMLResponse(content=html_content)
