"""add order priority

Revision ID: c29b740f4c61
Revises: 372edfadec2d
Create Date: 2024-12-10 01:44:29.741429

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c29b740f4c61'
down_revision = '372edfadec2d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority', sa.INTEGER(), server_default='1', nullable=False))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('priority')

    # ### end Alembic commands ###
