import os
import time
import redis
from booster import SuperViewBooster

r = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)

print("Worker started, waiting for jobs...")

while True:
    jid = r.rpop("queue:boost")
    if not jid:
        time.sleep(3)
        continue

    job = r.hgetall(f"job:{jid}")
    if not job:
        continue
    if job.get("status") == "cancelled":
        continue

    r.hset(f"job:{jid}", "status", "running")
    print(f"Running job {jid}: {job['url']}")

    def stop_flag():
        return r.hget(f"job:{jid}", "status") == "cancelled"

    def progress_cb(success, fail, submitted):
        r.hset(f"job:{jid}", mapping={
            "success": success,
            "fail": fail,
            "submitted": submitted,
        })

    try:
        booster = SuperViewBooster()
        proxies = booster.get_proxies_online()
        if not proxies:
            raise Exception("no proxy")
        booster.working_proxies = proxies[:booster.MAX_PROXIES]

        booster.boost_views(
            job["url"],
            int(job["total_views"]),
            float(job["delay"]),
            int(job["workers"]),
            stop_flag=stop_flag,
            progress_cb=progress_cb,
        )

        r.hset(f"job:{jid}", mapping={
            "status": "finished",
            "success": booster.success_count,
            "fail": booster.fail_count,
        })
    except Exception as e:
        r.hset(f"job:{jid}", mapping={"status": "failed", "error": str(e)})
        print(f"Job {jid} failed: {e}")
