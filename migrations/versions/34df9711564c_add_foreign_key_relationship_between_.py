"""Add foreign key relationship between resume_results and job_profiles

Revision ID: 34df9711564c
Revises: a2b8eeb58a96
Create Date: 2024-12-14 17:37:27.013731

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '34df9711564c'
down_revision = 'a2b8eeb58a96'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('resume_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('resume_name', sa.String(length=255), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('resume_path', sa.String(length=255), nullable=False),
    sa.Column('job_profile_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('resume_results')
    # ### end Alembic commands ###
