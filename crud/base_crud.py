from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


class BaseCRUD:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)
