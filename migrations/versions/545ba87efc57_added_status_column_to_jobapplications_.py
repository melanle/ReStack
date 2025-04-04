"""Added Status column to JobApplications Table

Revision ID: 545ba87efc57
Revises: 0369000de2d3
Create Date: 2025-01-21 15:32:53.242599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '545ba87efc57'
down_revision = '0369000de2d3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job_applications', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###
