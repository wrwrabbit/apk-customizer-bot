import sqlalchemy as sa

from models import Base


class MessageToDelete(Base):
    __tablename__ = "messages_to_delete"

    user_id = sa.Column(sa.BIGINT, primary_key=True)
    message_id = sa.Column(sa.Integer, primary_key=True)

    sent_date = sa.Column(
        sa.DateTime,
        nullable=False,
        server_default=sa.text("(CURRENT_TIMESTAMP)"),
    )
