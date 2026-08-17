from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict
import uuid

app = FastAPI(title="Ad-Hoc OSINT Discovery Engine")

class SeedInput(BaseModel):
    seed_type: str
    seed_value: str

class DiscoveryJob(BaseModel):
    job_id: str
    status: str
    discovered_nodes: List[Dict] = []
    confidence_score: float = 0.0

jobs: Dict[str, DiscoveryJob] = {}

def execute_discovery(job_id: str, seed: SeedInput):
    results = []
    if seed.seed_type == "username":
        results.append({"type": "profile", "platform": "GitHub", "url": f"https://github.com/{seed.seed_value}"})
    jobs[job_id].discovered_nodes = results
    jobs[job_id].confidence_score = 0.85 if results else 0.0
    jobs[job_id].status = "completed"

@app.post("/api/v1/search", response_model=DiscoveryJob)
async def start_search(seed: SeedInput, background_tasks: BackgroundTasks):
    if seed.seed_type not in ["username", "email", "image_url"]:
        raise HTTPException(status_code=400, detail="Invalid seed type")
    
    job_id = str(uuid.uuid4())
    job = DiscoveryJob(job_id=job_id, status="processing")
    jobs[job_id] = job
    background_tasks.add_task(execute_discovery, job_id, seed)
    return job

@app.get("/api/v1/results/{job_id}", response_model=DiscoveryJob)
async def get_results(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]
