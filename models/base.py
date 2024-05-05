from typing import Literal

from sqlalchemy import MetaData
from sqlalchemy.orm import as_declarative

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
_on_T = Literal["SET NULL", "CASCADE"]


@as_declarative(metadata=MetaData(naming_convention=convention))
class Base:
    metadata: MetaData
    __tablename__: str
