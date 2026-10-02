from jobhunt_api import db


def test_shared_catalogue_tables_exist(client, db_ready):
    rows = db.fetch_all(
        """
        SELECT tablename AS name
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename IN (
            'source_definitions','source_runs','raw_captures','companies',
            'catalogue_jobs','job_versions','job_sources','job_liveness','job_matches'
          )
        """
    )
    tables = {row["name"] for row in rows}
    assert tables == {
        "source_definitions",
        "source_runs",
        "raw_captures",
        "companies",
        "catalogue_jobs",
        "job_versions",
        "job_sources",
        "job_liveness",
        "job_matches",
    }


def test_public_ats_sources_are_seeded_and_disabled(client, db_ready):
    rows = db.fetch_all(
        """
        SELECT source_id, implementation_status, enabled, geographic_scope, retention_days
        FROM source_definitions
        WHERE source_id IN ('ashby', 'greenhouse', 'lever')
        ORDER BY source_id
        """,
    )
    assert [r["source_id"] for r in rows] == ["ashby", "greenhouse", "lever"]
    assert all(r["implementation_status"] == "planned" for r in rows)
    assert all(r["enabled"] is False for r in rows)
    assert all("IN" in r["geographic_scope"] for r in rows)
    assert all(r["retention_days"] == 30 for r in rows)


def test_raw_captures_require_retention_until(client, db_ready):
    greenhouse = db.fetch_one("SELECT source_id FROM source_definitions WHERE source_id = 'greenhouse'")
    assert greenhouse
    try:
        db.execute(
            """
            INSERT INTO raw_captures (source_id, content_hash, acquisition_mode, retention_until)
            VALUES ('greenhouse', 'hash-1', 'public_job_board_api', now() + interval '30 days')
            """
        )
        row = db.fetch_one("SELECT retention_until FROM raw_captures WHERE content_hash = 'hash-1'")
        assert row["retention_until"] is not None
    finally:
        db.execute("DELETE FROM raw_captures WHERE content_hash = 'hash-1'")
