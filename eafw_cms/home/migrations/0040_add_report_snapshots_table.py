from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0039_fix_admin_whca_tiles_function"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE TABLE IF NOT EXISTS gha.report_snapshots (
    id SERIAL PRIMARY KEY,
    assessment_id INTEGER NOT NULL UNIQUE
        REFERENCES gha.expert_assessments(id)
        ON DELETE CASCADE,
    snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_report_snapshots_assessment_id
    ON gha.report_snapshots (assessment_id);

CREATE INDEX IF NOT EXISTS idx_report_snapshots_updated_at
    ON gha.report_snapshots (updated_at DESC);
            """,
            reverse_sql="""
DROP TABLE IF EXISTS gha.report_snapshots CASCADE;
            """,
        )
    ]

