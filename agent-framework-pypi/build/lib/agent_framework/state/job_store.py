from __future__ import annotations

import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from pydantic import BaseModel
except Exception:  # pydantic should be present, but guard just in case
    BaseModel = object  # type: ignore

from ..base import BaseJobStore


class PendingAction(BaseModel):  # type: ignore[misc]
    worker: str
    tool: str
    args: Dict[str, Any]
    manager: Optional[str] = None
    resume_token: Optional[str] = None


class Job(BaseModel):  # type: ignore[misc]
    job_id: str
    status: str = "running"  # running | awaiting_approval | paused | completed
    orchestrator_plan: Optional[Dict[str, Any]] = None
    manager_plans: Dict[str, Dict[str, Any]] = {}
    phase_index_by_manager: Dict[str, int] = {}
    pending_action: Optional[PendingAction] = None
    approvals: Dict[str, bool] = {}
    executed_actions: list[str] = []  # tool+args signatures executed successfully
    last_result_summary: Optional[str] = None
    created_at: float = 0.0
    updated_at: float = 0.0


class FileJobStore(BaseJobStore):
    """Simple file-backed job store. JSON per job under a base directory.

    Not optimized for heavy concurrency, but safe enough for single-node or low-QPS.
    Writes are atomic via temp file + rename.
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        base = base_dir or os.getenv("AGENT_JOB_STORE_DIR", "jobs")
        self.base_dir = Path(base).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        # sanitize job_id to filename-ish
        safe = "".join(ch for ch in job_id if ch.isalnum() or ch in ("-", "_"))
        if not safe:
            safe = "job"
        return self.base_dir / f"{safe}.json"

    def get_job(self, job_id: str) -> Optional[Job]:
        p = self._path(job_id)
        if not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return Job(**data)
        except Exception:
            return None

    def create_job(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        if job:
            return job
        now = time.time()
        job = Job(job_id=job_id, created_at=now, updated_at=now)
        self.save_job(job)
        return job

    def save_job(self, job: Job) -> None:
        job.updated_at = time.time()
        p = self._path(job.job_id)
        tmp = p.with_suffix(".json.tmp")
        payload = job.model_dump() if hasattr(job, "model_dump") else asdict(job)  # type: ignore[arg-type]
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)

    def update_orchestrator_plan(self, job_id: str, plan: Dict[str, Any]) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        job.orchestrator_plan = plan
        self.save_job(job)

    def update_manager_plan(self, job_id: str, manager: str, plan: Dict[str, Any]) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        job.manager_plans = dict(job.manager_plans or {})
        job.manager_plans[manager] = plan
        # Reset phase index if not present
        indices = dict(job.phase_index_by_manager or {})
        indices.setdefault(manager, 0)
        job.phase_index_by_manager = indices
        self.save_job(job)

    def bump_phase(self, job_id: str, manager: str) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        indices = dict(job.phase_index_by_manager or {})
        cur = int(indices.get(manager, 0))
        indices[manager] = cur + 1
        job.phase_index_by_manager = indices
        self.save_job(job)

    def save_pending_action(
        self,
        job_id: str,
        *,
        worker: str,
        tool: str,
        args: Dict[str, Any],
        manager: Optional[str] = None,
        resume_token: Optional[str] = None,
    ) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        job.pending_action = PendingAction(worker=worker, tool=tool, args=dict(args or {}), manager=manager, resume_token=resume_token)
        job.status = "awaiting_approval"
        self.save_job(job)

    def clear_pending_action(self, job_id: str, *, new_status: Optional[str] = None) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        job.pending_action = None
        if new_status:
            job.status = new_status
        else:
            # default to running if not explicitly completed/paused
            job.status = "running"
        self.save_job(job)

    def save_approvals(self, job_id: str, approvals: Dict[str, bool]) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        m = dict(job.approvals or {})
        m.update(dict(approvals or {}))
        job.approvals = m
        self.save_job(job)

    def add_executed_action(self, job_id: str, signature: str) -> None:
        job = self.get_job(job_id) or self.create_job(job_id)
        sigs = list(job.executed_actions or [])
        if signature not in sigs:
            sigs.append(signature)
        job.executed_actions = sigs
        self.save_job(job)

    def has_executed_action(self, job_id: str, signature: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        try:
            return signature in (job.executed_actions or [])
        except Exception:
            return False


_JOB_STORE_SINGLETON: Optional[FileJobStore] = None


def get_job_store() -> FileJobStore:
    global _JOB_STORE_SINGLETON
    if _JOB_STORE_SINGLETON is None:
        _JOB_STORE_SINGLETON = FileJobStore()
    return _JOB_STORE_SINGLETON
