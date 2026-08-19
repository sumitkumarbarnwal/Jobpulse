"""
Jobs REST API endpoints.

GET  /api/jobs          — Paginated list with optional filters
GET  /api/jobs/{id}     — Single job detail
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.job import Job
from app.schemas.job import JobListResponse, JobOut

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, max_length=200, description="Full-text search on title, company, location"),
    remote: bool | None = Query(None, description="Filter by remote status"),
    location: str | None = Query(None, max_length=200, description="Filter by location (partial match)"),
    source: str | None = Query(None, max_length=64, description="Filter by source name"),
    db: Session = Depends(get_db),
):
    """
    Return a paginated list of job listings.

    Filters:
        search    — case-insensitive match on title, company, and location
        remote    — true/false
        location  — partial case-insensitive match
        source    — exact match on source name

    Pagination:
        page  — 1-indexed page number
        limit — records per page (max 100)
    """
    query = db.query(Job)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.title.ilike(term),
                Job.company.ilike(term),
                Job.location.ilike(term),
            )
        )

    if remote is not None:
        query = query.filter(Job.remote == remote)

    if location:
        query = query.filter(Job.location.ilike(f"%{location.strip()}%"))

    if source:
        query = query.filter(Job.source == source.strip())

    total = query.count()

    jobs = (
        query
        .order_by(Job.published_at.desc().nullslast(), Job.first_seen_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    pages = max(1, -(-total // limit))  # ceiling division

    return JobListResponse(
        jobs=[JobOut.model_validate(j) for j in jobs],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Return a single job by internal ID."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)
