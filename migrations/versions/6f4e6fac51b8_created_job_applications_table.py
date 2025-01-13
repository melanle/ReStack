"""Created Job Applications Table

Revision ID: 6f4e6fac51b8
Revises: d27dfa5f5788
Create Date: 2025-01-01 23:28:44.613156

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f4e6fac51b8'
down_revision = 'd27dfa5f5788'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('job_applications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('job_id', sa.Integer(), nullable=False),
    sa.Column('resume_path', sa.String(length=255), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('applied_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['job_id'], ['job_profiles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('job_applications')
    # ### end Alembic commands ###
