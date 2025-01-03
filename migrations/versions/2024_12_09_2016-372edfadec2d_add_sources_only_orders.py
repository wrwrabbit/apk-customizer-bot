"""add sources only orders

Revision ID: 372edfadec2d
Revises: f120292fa0f5
Create Date: 2024-12-09 20:16:19.795002

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '372edfadec2d'
down_revision = 'f120292fa0f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sources_only', sa.BOOLEAN(), server_default='FALSE', nullable=False))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('sources_only')

    # ### end Alembic commands ###