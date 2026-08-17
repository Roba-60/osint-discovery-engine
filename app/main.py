from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import networkx as nx
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
    max_depth: Optional[int] = Field(default=1, ge=1, le=3)

class DiscoveryJob(BaseModel):
    job_id: str
    status: str
    discovered_nodes: List[Dict[str, Any]] = []
    graph_network: Dict[str, Any] = {}
    confidence_score: float = 0.0

    class Config:
        from_attributes = True

async def execute_discovery(job_id: str, seed_type: str, seed_value: str, max_depth: int = 1):
    discovered_targets = set()
    queue = [(seed_type, seed_value, 0)]
    all_results = []
    
    while queue:
        curr_type, curr_val, depth = queue.pop(0)
        if (curr_type, curr_val) in discovered_targets:
            continue
        
        discovered_targets.add((curr_type, curr_val))
        
        if curr_type == "username":
            results = await search_public_username(curr_val)
            all_results.extend(results)
            
            # If multi-hop pivoting enabled, queue discovered handles
            if depth + 1 < max_depth:
                for res in results:
                    if "linked_username" in res:
                        queue.append(("username", res["linked_username"], depth + 1))

    graph_builder = IdentityGraphBuilder()
    graph_summary = graph_builder.build_identity_network(seed_type, seed_value, all_results)

    db = SessionLocal()
    try:
        job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
        if job:
            job.discovered_nodes = all_results
            job.graph_network = graph_summary
            job.confidence_score = min(len(all_results) * 0.25, 1.0)
            job.status = "completed"
            db.commit()
    finally:
        db.close()

def run_async_job(job_id: str, seed_type: str, seed_value: str, max_depth: int):
    asyncio.run(execute_discovery(job_id, seed_type, seed_value, max_depth))

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

    background_tasks.add_task(run_async_job, job_id, seed.seed_type, seed.seed_value, seed.max_depth)
    return db_job

@app.get("/api/v1/results/{job_id}", response_model=DiscoveryJob)
async def get_results(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/api/v1/export/{job_id}/graphml")
async def export_graphml(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobModel).filter(JobModel.job_id == job_id).first()
    if not job or job.status != "completed":
        raise HTTPException(status_code=404, detail="Job not found or incomplete")

    # Reconstruct NetworkX Graph from JSON node-link structure
    raw_graph_data = job.graph_network.get("graph_data", {})
    G = nx.node_link_graph(raw_graph_data)

    # Generate GraphML string in memory
    graphml_content = "\n".join(nx.generate_graphml(G))

    return Response(
        content=graphml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="osint_graph_{job_id}.graphml"'
        }
    )

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
            
            Download GraphML
        
        

        
    
    
    """
    return HTMLResponse(content=html_content)
