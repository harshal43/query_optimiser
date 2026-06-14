"""initial schema — 7 tables

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from __future__ import annotations
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name        TEXT NOT NULL UNIQUE,
            warehouse   TEXT NOT NULL DEFAULT 'COMPUTE_WH',
            warehouse_size TEXT NOT NULL DEFAULT 'X-Small',
            standardization_rules JSONB NOT NULL DEFAULT '{}',
            ab_test_config        JSONB NOT NULL DEFAULT '{}',
            enforcement_level     TEXT NOT NULL DEFAULT 'passive',
            created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            query_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_text        TEXT NOT NULL,
            query_hash        TEXT NOT NULL,
            query_preview     TEXT,
            team_id           UUID REFERENCES teams(team_id),
            warehouse         TEXT,
            warehouse_size    TEXT,
            classification    TEXT,
            severity          TEXT CHECK (severity IN ('critical','high','medium','low')),
            issue_type        TEXT,
            execution_metrics JSONB DEFAULT '{}',
            ingestion_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            source            TEXT DEFAULT 'snowflake',
            status            TEXT DEFAULT 'pending_review'
        )
    """)
    op.execute("CREATE INDEX idx_queries_team_id_btree ON queries (team_id)")
    op.execute("CREATE INDEX idx_queries_severity_btree ON queries (severity)")
    op.execute("CREATE INDEX idx_queries_status_btree ON queries (status)")
    op.execute("CREATE INDEX idx_queries_ingestion_btree ON queries (ingestion_timestamp)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS optimizations (
            optimization_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_id           UUID NOT NULL REFERENCES queries(query_id),
            diagnosis          JSONB DEFAULT '{}',
            variants           JSONB DEFAULT '[]',
            cost_predictions   JSONB DEFAULT '{}',
            validation_results JSONB DEFAULT '{}',
            recommended_variant TEXT,
            user_selected_variant TEXT,
            status             TEXT DEFAULT 'pending',
            created_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_optimizations_query_id ON optimizations (query_id)")
    op.execute("CREATE INDEX idx_optimizations_status ON optimizations (status)")
    op.execute("CREATE INDEX idx_optimizations_diagnosis_gin ON optimizations USING GIN (diagnosis)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            optimization_id   UUID NOT NULL REFERENCES optimizations(optimization_id),
            user_action       TEXT NOT NULL CHECK (user_action IN ('approved','rejected','modified')),
            rejection_reason  TEXT,
            actual_metrics    JSONB DEFAULT '{}',
            prediction_accuracy JSONB DEFAULT '{}',
            actor             TEXT,
            created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_feedback_optimization_id ON feedback (optimization_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS techniques (
            technique_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name              TEXT NOT NULL UNIQUE,
            category          TEXT,
            success_rate      FLOAT DEFAULT 0.0,
            failure_rate      FLOAT DEFAULT 0.0,
            application_count INTEGER DEFAULT 0,
            last_updated      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_tests (
            test_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_id            UUID NOT NULL REFERENCES queries(query_id),
            optimization_id     UUID REFERENCES optimizations(optimization_id),
            variant_assignment  JSONB DEFAULT '{}',
            control_metrics     JSONB DEFAULT '{}',
            variant_metrics     JSONB DEFAULT '{}',
            traffic_split       JSONB DEFAULT '{"control": 100, "optimized": 0}',
            status              TEXT DEFAULT 'shadow'
                                CHECK (status IN ('shadow','active','completed','rolled_back')),
            p_value             FLOAT,
            started_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at        TIMESTAMP WITH TIME ZONE
        )
    """)
    op.execute("CREATE INDEX idx_ab_tests_query_id ON ab_tests (query_id)")
    op.execute("CREATE INDEX idx_ab_tests_status ON ab_tests (status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp     TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            actor         TEXT NOT NULL,
            action        TEXT NOT NULL,
            resource_type TEXT,
            resource_id   UUID,
            payload_hash  TEXT,
            payload       JSONB DEFAULT '{}'
        )
    """)
    op.execute("CREATE INDEX idx_audit_log_timestamp ON audit_log (timestamp)")
    op.execute("CREATE INDEX idx_audit_log_resource ON audit_log (resource_type, resource_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS ab_tests CASCADE")
    op.execute("DROP TABLE IF EXISTS techniques CASCADE")
    op.execute("DROP TABLE IF EXISTS feedback CASCADE")
    op.execute("DROP TABLE IF EXISTS optimizations CASCADE")
    op.execute("DROP TABLE IF EXISTS queries CASCADE")
    op.execute("DROP TABLE IF EXISTS teams CASCADE")
