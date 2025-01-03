"""add workers id to order

Revision ID: 2699b2a4016b
Revises: 853a1a8c6f87
Create Date: 2024-08-07 22:46:38.321562

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2699b2a4016b'
down_revision = '853a1a8c6f87'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('worker_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_orders_worker_id'), ['worker_id'], unique=True)
        batch_op.create_foreign_key(batch_op.f('fk_orders_worker_id_workers'), 'workers', ['worker_id'], ['id'], ondelete='SET NULL')

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_orders_worker_id_workers'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_orders_worker_id'))
        batch_op.drop_column('worker_id')

    # ### end Alembic commands ###
