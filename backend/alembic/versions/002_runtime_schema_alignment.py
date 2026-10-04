"""Align legacy initial schema with current runtime models.

Revision ID: 002_runtime_schema_alignment
Revises: 001_initial_schema
"""
from alembic import op
import sqlalchemy as sa


revision = "002_runtime_schema_alignment"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table_names = set(sa.inspect(op.get_bind()).get_table_names())
    if "_alembic_tmp_assessments" in table_names:
        pending_rows = op.get_bind().execute(
            sa.text("SELECT COUNT(*) FROM _alembic_tmp_assessments")
        ).scalar_one()
        if pending_rows:
            raise RuntimeError(
                "An interrupted assessments migration left rows in _alembic_tmp_assessments; "
                "manual reconciliation is required before retrying."
            )
        op.drop_table("_alembic_tmp_assessments")

    inspector = sa.inspect(op.get_bind())
    assessment_columns = {column["name"] for column in inspector.get_columns("assessments")}
    assessment_foreign_keys = inspector.get_foreign_keys("assessments")
    has_parent_foreign_key = any(
        foreign_key.get("constrained_columns") == ["parent_assessment_id"]
        for foreign_key in assessment_foreign_keys
    )

    with op.batch_alter_table("assessments") as batch_op:
        if "guideline_version" not in assessment_columns:
            batch_op.add_column(
                sa.Column("guideline_version", sa.Integer(), nullable=False, server_default="1")
            )
        if "application_version" not in assessment_columns:
            batch_op.add_column(
                sa.Column("application_version", sa.Integer(), nullable=False, server_default="1")
            )
        if "run_number" not in assessment_columns:
            batch_op.add_column(
                sa.Column("run_number", sa.Integer(), nullable=False, server_default="1")
            )
        if "parent_assessment_id" not in assessment_columns:
            batch_op.add_column(sa.Column("parent_assessment_id", sa.String(36), nullable=True))
        if "raw_analysis_payload" not in assessment_columns:
            batch_op.add_column(sa.Column("raw_analysis_payload", sa.JSON(), nullable=True))
        if not has_parent_foreign_key:
            batch_op.create_foreign_key(
                "fk_assessments_parent_assessment_id",
                "assessments",
                ["parent_assessment_id"],
                ["id"],
                ondelete="SET NULL",
            )

    document_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("document_versions")}
    with op.batch_alter_table("document_versions") as batch_op:
        if "file_path" in document_columns and "storage_path" not in document_columns:
            batch_op.alter_column(
                "file_path",
                new_column_name="storage_path",
                existing_type=sa.String(512),
                type_=sa.String(512),
                existing_nullable=False,
                nullable=False,
            )
        if "file_size_bytes" in document_columns:
            batch_op.alter_column(
                "file_size_bytes",
                existing_type=sa.Integer(),
                nullable=True,
            )

    requirement_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("requirements")}
    if "created_at" in requirement_columns:
        with op.batch_alter_table("requirements") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=True)

    mapping_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("requirement_mappings")}
    if "ai_status" not in mapping_columns:
        op.add_column("requirement_mappings", sa.Column("ai_status", sa.String(50), nullable=True))
    op.execute("UPDATE requirement_mappings SET ai_status = status WHERE ai_status IS NULL")
    with op.batch_alter_table("requirement_mappings") as batch_op:
        batch_op.alter_column("ai_status", existing_type=sa.String(50), nullable=False)
        batch_op.alter_column("assessment_id", existing_type=sa.String(36), nullable=True)
        batch_op.alter_column("status", existing_type=sa.String(50), nullable=True)
        batch_op.alter_column("evidence", existing_type=sa.Text(), nullable=True)
        batch_op.alter_column("source_document", existing_type=sa.String(255), nullable=True)
        batch_op.alter_column("reasoning", existing_type=sa.Text(), nullable=True)
        if "reviewer_evidence" not in mapping_columns:
            batch_op.add_column(sa.Column("reviewer_evidence", sa.Text(), nullable=True))
        if "reviewer_citation" not in mapping_columns:
            batch_op.add_column(sa.Column("reviewer_citation", sa.String(255), nullable=True))
        if not any(
            constraint.get("column_names") == ["requirement_id"]
            for constraint in sa.inspect(op.get_bind()).get_unique_constraints("requirement_mappings")
        ):
            batch_op.create_unique_constraint(
                "uq_requirement_mappings_requirement_id",
                ["requirement_id"],
            )

    unsupported_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("unsupported_claims")}
    if "created_at" in unsupported_columns:
        with op.batch_alter_table("unsupported_claims") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=True)

    clarification_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("clarification_questions")}
    if "created_at" in clarification_columns:
        with op.batch_alter_table("clarification_questions") as batch_op:
            batch_op.alter_column("created_at", existing_type=sa.DateTime(), nullable=True)


def downgrade() -> None:
    raise NotImplementedError("Runtime schema alignment is intentionally irreversible.")