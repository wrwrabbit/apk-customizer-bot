"""add update tag to order

Revision ID: 17c183fddb02
Revises: a1b81ff163a8
Create Date: 2024-09-24 18:08:37.070991

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '17c183fddb02'
down_revision = 'a1b81ff163a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('update_tag', sa.String(), nullable=True))

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_column('update_tag')

    # ### end Alembic commands ###
