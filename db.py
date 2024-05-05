from sqlalchemy import create_engine
import config

db_url = (
    f"postgresql://"
    f"{config.DATABASE_USER}:"
    f"{config.DATABASE_PASSWORD}@"
    f"{config.DATABASE_HOST}:"
    f"{config.DATABASE_PORT}/"
    f"{config.DATABASE_DB}"
)

engine = create_engine(
    db_url,
    echo=False,
)
