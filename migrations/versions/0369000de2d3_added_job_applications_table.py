"""Added job_applications table

Revision ID: 0369000de2d3
Revises: 39ef3d3a45f1
Create Date: 2025-01-19 16:43:19.730015

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0369000de2d3'
down_revision = '39ef3d3a45f1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('job_applications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('job_profile_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('applied_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('job_applications')
    # ### end Alembic commands ###
