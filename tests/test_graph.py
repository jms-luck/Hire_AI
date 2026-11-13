from types import SimpleNamespace

from backend.app.services.graph import APPLICATION_SYNC_QUERY, fallback_graph, neo4j_uri_candidates, parse_skills, reset_neo4j_connections


def test_parse_skills_normalizes_and_deduplicates() -> None:
    skills = parse_skills("{'Python', 'SQL', 'python'}")
    assert {skill.casefold() for skill in skills} == {"python", "sql"}
    assert len(skills) == 2


def test_applicant_graph_contains_required_nodes_and_edges() -> None:
    job = SimpleNamespace(job_id=10, job_title="AI Engineer")
    candidate = SimpleNamespace(candidate_id=2, location="Remote")
    user = SimpleNamespace(name="Jane Doe", email="jane@example.com")
    resume = SimpleNamespace(resume_id=3, original_filename="jane.pdf", version=2)
    company = SimpleNamespace(company_id=4, company_name="Hire AI")
    graph = fallback_graph(job, candidate, user, resume, company, ["Python"], ["SQL"], 88.5, "JOB", "APPLIED")
    assert {node["type"] for node in graph["nodes"]} == {"Candidate", "Resume", "Job", "Company", "Skill"}
    assert {edge["type"] for edge in graph["edges"]} >= {"HAS_RESUME", "APPLIED_TO", "SUBMITTED_FOR", "AT_COMPANY", "REQUIRES", "HAS_SKILL", "MISSING_SKILL"}
    missing_edge = next(edge for edge in graph["edges"] if edge["type"] == "MISSING_SKILL")
    assert missing_edge == {"source": "candidate:2", "target": "skill:sql", "type": "MISSING_SKILL"}


def test_suitability_sync_does_not_erase_existing_application_metadata() -> None:
    assert "coalesce(row.application_id,a.application_id)" in APPLICATION_SYNC_QUERY
    assert "coalesce(row.applied_at,a.applied_at)" in APPLICATION_SYNC_QUERY


def test_neo4j_uri_candidates_include_container_fallbacks(monkeypatch) -> None:
    reset_neo4j_connections()
    monkeypatch.setattr("backend.app.services.graph.running_in_container", lambda: True)
    neo4j_uri_candidates.cache_clear()

    assert neo4j_uri_candidates("bolt://localhost:7687") == (
        "bolt://localhost:7687",
        "bolt://host.docker.internal:7687",
        "bolt://neo4j:7687",
    )


def test_neo4j_uri_candidates_leave_remote_hosts_unchanged(monkeypatch) -> None:
    reset_neo4j_connections()
    monkeypatch.setattr("backend.app.services.graph.running_in_container", lambda: True)
    neo4j_uri_candidates.cache_clear()

    assert neo4j_uri_candidates("bolt://graph.example.com:7687") == ("bolt://graph.example.com:7687",)
