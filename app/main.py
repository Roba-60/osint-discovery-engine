from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import asyncio
from app.scrapers import search_public_username
from app.graph import IdentityGraphBuilder

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

jobs: Dict[str, DiscoveryJob] = {}

async def execute_discovery(job_id: str, seed: SeedInput):
    results = []
    if seed.seed_type == "username":
        results = await search_public_username(seed.seed_value)
    
    graph_builder = IdentityGraphBuilder()
    graph_summary = graph_builder.build_identity_network(seed.seed_type, seed.seed_value, results)

    jobs[job_id].discovered_nodes = results
    jobs[job_id].graph_network = graph_summary
    jobs[job_id].confidence_score = min(len(results) * 0.3, 1.0)
    jobs[job_id].status = "completed"

def run_async_job(job_id: str, seed: SeedInput):
    asyncio.run(execute_discovery(job_id, seed))

@app.post("/api/v1/search", response_model=DiscoveryJob)
async def start_search(seed: SeedInput, background_tasks: BackgroundTasks):
    if seed.seed_type not in ["username", "email", "image_url"]:
        raise HTTPException(status_code=400, detail="Invalid seed type")
    
    job_id = str(uuid.uuid4())
    job = DiscoveryJob(job_id=job_id, status="processing")
    jobs[job_id] = job
    background_tasks.add_task(run_async_job, job_id, seed)
    return job

@app.get("/api/v1/results/{job_id}", response_model=DiscoveryJob)
async def get_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
