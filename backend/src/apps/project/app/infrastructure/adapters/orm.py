from sqlalchemy import MetaData
from sqlalchemy.orm import registry


metadata = MetaData()
mapper_registry = registry(metadata=metadata)


def start_mappers() -> None:
    return None
