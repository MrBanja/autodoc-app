from typing import Optional, Callable, Union, Type, Any

from loguru import logger
from sqlalchemy import delete, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

from database.db_core import Session, Base, Engine


class DbController:
    """
    Main parent class for all DB models
    Implements CRUD methods
    """

    def __init__(self, **kwargs):
        pass

    def as_dict(self):
        """
        Returns sqlalchemy object as a dict
        :return:
        """
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    @classmethod
    def _make_query(
            cls,
            func: Callable,
            field: str | None,
            custom_filter: BinaryExpression | BooleanClauseList | bool | None,
            custom_field: Any | None = None,
            **kwargs,
    ):
        if field is not None:
            query = func(cls.__dict__[field])
        elif custom_field is not None:
            query = func(custom_field)
        else:
            query = func(cls)
        if custom_filter is not None:
            query = query.where(custom_filter)
        else:
            query = query.filter_by(**kwargs)
        return query

    @classmethod
    async def get(
            cls,
            field: Optional[str] = None,
            custom_filter: BinaryExpression | BooleanClauseList | bool | None = None,
            **kwargs,
    ):
        """
        Get one or None class instance
        :param field: str, if needed to return only one field of instance
        :param custom_filter: to pass custom filer, like cls.iid.in_([1,2,3])
        :param kwargs: fields for apply filters to request, like iid=1
        :return: instance of class, None or one field of class
        """
        async with Session() as session:
            async with session.begin():
                request = await session.execute(
                    cls._make_query(select, field, custom_filter, **kwargs),
                )
                return request.scalars().first()

    @classmethod
    async def get_list(
            cls,
            field: Optional[str] = None,
            custom_filter: Optional[Union[BinaryExpression, BooleanClauseList]] = None,
            order_by: Optional[Any] = None,
            limit: Optional[int] = None,
            custom_field: Optional[Any] = None,
            group_by: tuple[Any, ...] = (),
            **kwargs,
    ) -> list:
        """
        Get list of class instances
        :param custom_filter: to pass custom filer, like cls.iid.in_([1,2,3])
        :param field: str, if needed to return only one field of instance
        :param order_by: order_by field
        :param limit: limit results
        :param custom_field: custom fields or function needed to be passed to cls._make_query
        :param group_by: group_by results
        :param kwargs: fields for apply filters to request, like iid=1
        :return: list of instances
        """
        session = Session()
        async with session.begin():
            try:
                query = cls._make_query(select, field, custom_filter, custom_field, **kwargs)
                if order_by is not None:
                    query = query.order_by(order_by)
                if limit is not None:
                    query = query.limit(limit)
                if group_by:
                    query = query.group_by(*group_by)
                request = await session.execute(query)
                return request.scalars().all()
            except Exception as e:
                logger.exception(e)

    @classmethod
    async def get_all(cls, field: Optional[str] = None):
        """
        Get list of all class instances, SELECT * from cls;
        :param field: str, if needed to return only one field of instance
        :return: list of all instances of model
        """
        async with Session() as session:
            async with session.begin():
                if field is not None:
                    request = await session.execute(select(cls.__dict__[field]))
                else:
                    request = await session.execute(select(cls))
                return request.scalars().all()

    @classmethod
    async def create(cls, **kwargs):
        """
        Insert method
        :param kwargs: class attributes
        :return: new instance of class or None
        """
        async with Session() as session:
            async with session.begin():
                try:
                    new_instance = cls(**kwargs)
                    session.add(new_instance)
                    await session.commit()
                    return new_instance
                except IntegrityError as exp:
                    logger.warning(exp)
                    await session.rollback()
                    return str(exp)

    async def update(
        self,
        **kwargs,
    ):
        """
        Update instance fields
        :param kwargs: fields needed to update and new values
        :return: new instance of class or None
        """
        for k, v in kwargs.items():
            if k in self.__dict__.keys():
                self.__setattr__(k, v)
        async with Session() as session:
            async with session.begin():
                try:
                    session.add(self)
                    await session.commit()
                    return self
                except IntegrityError as exp:
                    logger.warning(exp)
                    await session.rollback()

    @classmethod
    async def commit_changes(cls, instances: list[Type[Base]]) -> Optional[list[Type[Base]]]:
        """
        Commit changes
        :param instances: any ORM initialised instances
        :return: instances or None
        """
        async with Session() as session:
            async with session.begin():
                for instance in instances:
                    session.add(instance)
                try:
                    await session.commit()
                    return instances
                except IntegrityError as exp:
                    logger.warning(exp)
                    await session.rollback()

    @classmethod
    async def remove(
            cls,
            custom_filter: BinaryExpression | BooleanClauseList | bool,
    ):
        """
        Method to delete entities
        :param custom_filter: where expression
        :return: bool, True if there's no error
        """
        async with Session() as session:
            async with session.begin():
                try:
                    await session.execute(delete(cls).where(custom_filter))
                    await session.commit()
                    return True
                except Exception as e:
                    logger.exception(e)
                    await session.rollback()
                    return False

    @classmethod
    async def execute_query(
            cls,
            query: str,
            **kwargs,
    ) -> CursorResult:
        """
        Method to execute raw sql query
        :param query: str, SQL query
        :return: Any
        """
        connection = Engine.connect()
        try:
            # without connection.begin it won't commit changes and will applies rollback
            async with connection.begin():
                return await connection.execute(text(query), kwargs)
        except Exception as e:
            logger.exception(f'Exception has been occurred {e}')
            raise

    async def delete(self) -> bool:
        return await self.remove(self.__class__.__dict__['id'] == self.__dict__['id'])
