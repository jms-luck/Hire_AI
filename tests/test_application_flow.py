from types import SimpleNamespace

from fastapi import BackgroundTasks

from backend.app.models import Company, JobPosting, Resume, User
from backend.app.routers.candidate import apply, sync_submitted_application
from backend.app.schemas.contracts import ApplicationCreate


def test_apply_commits_before_scheduling_derived_indexes() -> None:
    job = SimpleNamespace(job_id=9, status="ACTIVE", company_id=3)
    resume = SimpleNamespace(resume_id=7, candidate_id=4)
    user = SimpleNamespace(user_id=2)
    company = SimpleNamespace(company_id=3)
    events = []

    class FakeDb:
        def get(self, model, item_id):
            return {JobPosting: job, Resume: resume, User: user, Company: company}[model]

        def add(self, item):
            events.append("add")

        def commit(self):
            events.append("commit")

        def refresh(self, item):
            item.application_id = 11
            item.status = "APPLIED"
            item.applied_at = None
            events.append("refresh")

    background_tasks = BackgroundTasks()
    candidate = SimpleNamespace(candidate_id=4, user_id=2)
    result = apply(9, ApplicationCreate(resume_id=7), background_tasks, candidate, FakeDb())

    assert events == ["add", "commit", "refresh"]
    assert result.application_id == 11
    assert len(background_tasks.tasks) == 1
    assert background_tasks.tasks[0].func is sync_submitted_application