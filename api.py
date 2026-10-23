import os
import uuid
import redis
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
SECRET = os.environ.get("BOOST_SECRET", "doi_khoa")


class Req(BaseModel):
    url: str
    secret: str
    total_views: int = 1_000_000_000
    delay: float = 0.01
    workers: int = 1000


@app.get("/")
def root():
    return {"ok": True}


@app.post("/boost")
def boost(req: Req):
    if req.secret != SECRET:
        return {"error": "unauthorized"}
    jid = str(uuid.uuid4())
    r.hset(f"job:{jid}", mapping={
        "status": "queued",
        "url": req.url,
        "total_views": req.total_views,
        "delay": req.delay,
        "workers": req.workers,
        "success": 0,
        "fail": 0,
        "submitted": 0,
    })
    r.lpush("queue:boost", jid)
    return {"job_id": jid, "status": "queued"}


@app.get("/status/{jid}")
def status(jid: str):
    d = r.hgetall(f"job:{jid}")
    if not d:
        return {"error": "not found"}
    d["job_id"] = jid
    return d


@app.post("/stop/{jid}")
def stop(jid: str):
    if not r.exists(f"job:{jid}"):
        return {"error": "not found"}
    r.hset(f"job:{jid}", "status", "cancelled")
    return {"job_id": jid, "status": "cancelled"}
