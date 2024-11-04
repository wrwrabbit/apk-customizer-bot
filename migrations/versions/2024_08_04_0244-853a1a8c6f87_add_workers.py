"""add workers

Revision ID: 853a1a8c6f87
Revises: f6aab24ed45e
Create Date: 2024-08-04 02:44:03.859508

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '853a1a8c6f87'
down_revision = 'd9b8d16457d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('workers',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('record_created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('ip', sa.String(), nullable=True),
    sa.Column('last_online_date', sa.DateTime(), server_default='1970-01-01 00:00:00', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workers'))
    )
    with op.batch_alter_table('workers', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workers_name'), ['name'], unique=True)

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('workers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workers_name'))

    op.drop_table('workers')
    # ### end Alembic commands ###
