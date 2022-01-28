import fastapi
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import load_only, decl_api
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy import asc, desc, func, Column
from sqlalchemy.sql.selectable import Select
from typing import Any, List, Optional, Union, Dict
from pydantic import create_model

from .status import StatusResponse
from .utility import CommonQueryGetter
from .log import logger


def create_status(code, message_server, message_client=None):
    if message_client is None:
        message_client = message_server
    return {"code": code, "message": message_server}


def create_response(data={}, meta={}, status={}):
    return {
        "data": data,
        "meta": meta,
        "status": status,
    }

async def update_data(session, tableModel, dataObject, newDataPydantic):
    updates = {}
    fields = [i for i in vars(tableModel) if "_" not in [i[0], i[-1]]]
    for key in fields:
        if key in newDataPydantic.__dict__:
            updates[key] = newDataPydantic.__dict__[key]
    for key, value in updates.items():
        setattr(dataObject, key, value)
    session.add(dataObject)
    await session.commit()
    await session.refresh(dataObject)

class StatusCreator(StatusResponse):
    """
    to add more status, edit dependencies/status.py in StatusResponse class
    """

    def __init__(self):
        self._applyStatusAsAttribute()

    def _applyStatusAsAttribute(self):
        allAttr = [i for i in vars(StatusResponse) if not "_" in [i[0], i[-1]]]
        for a in allAttr:
            def fetcher(attrName):
                def response(message=str(attrName).replace("_", " ")):
                    code = StatusResponse.__dict__[attrName]
                    return create_status(code, str(message))
                return response
            self.__dict__[a] = fetcher(a)


status = StatusCreator()
"""
- The default message is the status name
- You can add your custom message by inserting your message to the function
    - ex: status.success("great")
- To add more status, edit 'StatusResponse' class in dependencies/status.py
"""


def get_field(classModel):
    try:
        fields = [i for i in vars(classModel) if "_" not in [i[0], i[-1]]]
        columnFields = []
        for f in fields:
            if "comparator" in classModel.__dict__[f].__dict__:
                if (
                    "column"
                    in str(classModel.__dict__[f].__dict__["comparator"]).lower()
                ):
                    columnFields.append(f)
        return columnFields
    except:
        return []

def validate_field(modelField, targetField):
    if type(modelField) in [list, tuple, dict]:
        availableField = modelField
    else:
        availableField = get_field(modelField)
    return [i for i in targetField if i in availableField]

class SimpleCRUDBaseDeclaration:
    base = None
    
    @staticmethod
    def set_base(base: decl_api.DeclarativeMeta):
        if type(base) == decl_api.DeclarativeMeta:
            SimpleCRUDBaseDeclaration.base = base
        else:
            raise BaseException("Invalid Base")

def set_declarative_base(base: decl_api.DeclarativeMeta):
    return SimpleCRUDBaseDeclaration.set_base(base)

class Selector:
    """
    Selector Class, modifiying the sqlalchemy select
    """

    def __init__(self, *columns, **columnsKeyPair):
        """
        add your customer key by adding the key-value pair
            ex: Selector(uid = User.id, name = Profile.name)

        or

        define it automatically by just giving the column name
            ex: Selector(User.id, Profile.name)

        (this output column name will be user_id, profile_name)
        """
        if not SimpleCRUDBaseDeclaration.base:
            msg = "SQLAlchemy Declarative Base is not defined. please define it by using 'set_declarative_base'\n"
            msg += "    >>> from fastapi_simple_crud.dependencies import utils\n"
            msg += "    >>> utils.set_declarative_base(Base)"
            raise BaseException(msg)
        self.baseClass = SimpleCRUDBaseDeclaration.base.__subclasses__()
        if columnsKeyPair:
            self.columns = list(columnsKeyPair.values())
            self.columnsKeyPair = columnsKeyPair
        else:
            self.columns = columns
            self.columnsKeyPair = dict(zip(self.get_keys(), list(columns)))
        self.keys = list(self.columnsKeyPair.keys())

    @property
    def query(self):
        return select(*self.columns)

    def get_keys(self):
        keys = []
        for c in self.columns:
            className, key = str(c).split(".")
            className = self.check_belonging(className)
            keys.append(className + "_" + key)
        return keys

    def check_belonging(self, key):
        for c in self.baseClass:
            cKey = str(c).split("'")[1].split(".")[-1]
            if key == cKey:
                return c.__tablename__
        return key

    async def execute(self, session: AsyncSession, query: Select):
        data = []
        query = await session.execute(query)
        for q in query:
            data.append(dict(zip(self.keys, list(q))))
        return data


class QueryManager:
    def __init__(self, classModel):
        self.classModel = classModel

    @property
    def fields(self) -> list:
        return get_field(self.classModel)

    @property
    def rawQuery(self) -> Select:
        return select(self.classModel)

    def validate_fields(self, fields: list) -> list:
        if fields:
            return [i for i in fields if i in self.fields]
        return []


def QueryPaginator(
    getParams: CommonQueryGetter, _obj: Union[decl_api.DeclarativeMeta, Selector]
):
    """
    Query Paginator generator for single or multiple table
    """
    if type(_obj) == Selector:
        return QueryPaginatorMultiple(getParams, _obj)
    if _obj.__class__ == decl_api.DeclarativeMeta:
        if len(_obj.__mro__) == 3:
            return QueryPaginatorSingle(getParams, _obj)
    raise BaseException("Error Paginator")


class QueryPaginatorSingle(QueryManager):
    """
    Query Paginator for common use of paginating functions
    """

    def __init__(self, getParams: CommonQueryGetter, classModel):
        QueryManager.__init__(self, classModel)
        self.getParams = getParams
        if getParams.fields:
            self.filterFields = self.validate_fields(getParams.fields.split(","))
        else:
            self.filterFields = self.fields

    def filter(self, query: Select, fields: Optional[list] = None) -> Select:
        """
        filter the desired fields from the query (it will remains the primary key)
        """
        if not fields:
            fields = self.filterFields
        return query.options(load_only(*fields))

    def filter_primary_key(self, data: list) -> list:
        """
        primary key filter
        """
        newData = []
        for d in data:
            newPair = {}
            for key in d.__dict__:
                if key in self.filterFields:
                    newPair[key] = d.__dict__[key]
            newData.append(newPair)
        return newData

    def sort(self, query: Select, sortBy: str, sortType: str) -> Select:
        """
        sort your query by defining both the sortBy 'fields' and sortType 'asc'/'desc' parameters
        """
        if sortBy in self.fields:
            merchantOrder = self.classModel.__dict__[sortBy]
            for iSortType, orderMethod in [["asc", asc], ["desc", desc]]:
                if sortType == iSortType:
                    return query.order_by(orderMethod(merchantOrder))
        return query

    def paginate(self, query: Select, pageNo: int, limitPerPage: int) -> Select:
        """
        paginate query by defining page number and page limit
        """
        query = query.offset((pageNo - 1) * limitPerPage)
        query = query.limit(limitPerPage)
        return query

    async def execute_pagination(self, session: AsyncSession, query: Select) -> dict:
        """
        sort, filter and paginate the query with executed query outputs
        """
        query = self.filter(query)
        countAfterFilter = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        countAfterFilter = countAfterFilter.scalars().one()
        query = self.sort(query, self.getParams.sortBy, self.getParams.sortType)
        query = self.paginate(query, self.getParams.page, self.getParams.limit)
        query = await session.execute(query)
        datas = query.scalars().all()
        datas = self.filter_primary_key(datas)
        return create_response(
            data={"list": datas},
            meta={
                "page": self.getParams.page,
                "length": self.getParams.limit,
                "total": countAfterFilter,
            },
            status=status.success(),
        )


class QueryPaginatorMultiple:
    def __init__(self, getParams: CommonQueryGetter, selector: Selector):
        self.rawQuery = selector.query
        self.getParams = getParams
        self.selector = selector
        if getParams.fields:
            self.fields = validate_field(
                self.selector.keys, getParams.fields.split(",")
            )
        else:
            self.fields = self.selector.keys

    def filter(self, data: list, fields: Optional[list] = None) -> Select:
        """
        filter the desired fields from the query (it will remains the primary key)
        """
        if not fields:
            fields = self.fields
        newData = []
        for d in data:
            newPair = {}
            for k in d:
                if k in fields:
                    newPair[k] = d[k]
            newData.append(newPair)
        return newData

    def sort(self, query: Select, sortBy: str, sortType: str) -> Select:
        """
        sort your query by defining both the sortBy 'fields' and sortType 'asc'/'desc' parameters
        """
        if sortBy in self.fields:
            merchantOrder = self.selector.columnsKeyPair[sortBy]
            for iSortType, orderMethod in [["asc", asc], ["desc", desc]]:
                if sortType == iSortType:
                    return query.order_by(orderMethod(merchantOrder))
        return query

    def paginate(self, query: Select, pageNo: int, limitPerPage: int) -> Select:
        """
        paginate query by defining page number and page limit
        """
        query = query.offset((pageNo - 1) * limitPerPage)
        query = query.limit(limitPerPage)
        return query

    async def execute_pagination(self, session: AsyncSession, query: Select):
        countAfterFilter = await session.execute(
            select(func.count()).select_from(query.subquery())
        )
        countAfterFilter = countAfterFilter.scalars().one()
        query = self.sort(query, self.getParams.sortBy, self.getParams.sortType)
        query = self.paginate(query, self.getParams.page, self.getParams.limit)
        datas = await self.selector.execute(session, query)
        datas = self.filter(datas)
        return create_response(
            data={"list": datas},
            meta={
                "page": self.getParams.page,
                "length": self.getParams.limit,
                "total": countAfterFilter,
            },
            status=status.success(),
        )

## Future update
# class BaseLikeClause:
#     def __init__(self, classModel, *likeExpression, **likeClause):
#         self.classModel = classModel
#         self.likeExp = likeExpression
#         self.lc = self.filterEmptyClause(likeClause)

#     def applyLikeObject(self, query: Select, whereClauseDict, **WhereClauseKwargs):
#         WhereClauseKwargs.update(whereClauseDict)
#         self.wc.update(WhereClauseKwargs)
#         for w in self.we:
#             query = query.filter(w)
#         for key in self.wc:
#             query = query.where(self.classModel.__dict__[key] == self.wc[key])
#         return query
    
#     def filterEmptyClause(self, likeClauseInDict: dict):
#         newDict = {}
#         for key, val in likeClauseInDict.items():
#             if val != None:
#                 newDict[key] = val
#         return newDict

class BaseWhereClause:
    def __init__(self, classModel, *whereExpression, **whereClause):
        self.classModel = classModel
        self.we = whereExpression
        self.wc = whereClause

    def applyWhereObject(self, query: Select, whereClauseDict: Optional[dict] = {}, **WhereClauseKwargs):
        WhereClauseKwargs.update(whereClauseDict)
        self.wc.update(WhereClauseKwargs)
        self.wc = self.filterEmptyClause(self.wc)
        for w in self.we:
            query = query.where(w)
        for key in self.wc:
            query = query.where(self.classModel.__dict__[key] == self.wc[key])
        return query
    
    def filterEmptyClause(self, whereClauseInDict: dict):
        newDict = {}
        for key, val in whereClauseInDict.items():
            if val != None:
                newDict[key] = val
        return newDict

class BaseCRUD:
    def __init__(self, classModel):
        self.classModel = classModel

    def where(self, *whereExpression, **whereClause):
        return BaseWhereClause(self.classModel, *whereExpression, **whereClause)

    async def read_one(
            self,
            pydanticModel,
            session: AsyncSession
        ):
        try:
            query = select(self.classModel)
            for k, attr in pydanticModel.dict().items():
                if k in vars(self.classModel):
                    query = query.where(vars(self.classModel)[k]==attr)
            data = await session.execute(query)
            data = data.scalars().first()
            res = create_response(data=data, status=status.success())
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res
    
    async def read_many(
            self,
            getParams: CommonQueryGetter,
            session: AsyncSession,
            whereClauseObject: Optional[BaseWhereClause] = None,
            **whereClause
        ):
        try:
            paginator = QueryPaginator(getParams, self.classModel)
            query = paginator.rawQuery
            if whereClauseObject:
                query = whereClauseObject.applyWhereObject(query, whereClause)
            res = await paginator.execute_pagination(session, query)
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def read(self, getParams: CommonQueryGetter, session: AsyncSession):
        """
        with pagination
        """
        try:
            paginator = QueryPaginator(getParams, self.classModel)
            query = paginator.rawQuery
            res = await paginator.execute_pagination(session, query)
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def create(self, pydanticModel, session: AsyncSession):
        try:
            newData = self.classModel(**pydanticModel.dict())
            session.add(newData)
            await session.commit()
            await session.refresh(newData)
            res = create_response(status=status.success())
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res
    
    async def create_many(self, pydanticModelCollection, session: AsyncSession):
        try:
            dataCollection = pydanticModelCollection.dict()[self.classModel.__tablename__]
            createdObj = []
            statuses = []
            successCreate = 0
            failCreate = 0
            for data in dataCollection:
                try:
                    obj = self.classModel(**data)
                    session.add(obj)
                    createdObj.append(obj)                    
                    successCreate += 1
                    statuses.append(status.success())
                    await session.flush()
                except Exception as e:
                    failCreate += 1
                    statuses.append(status.error(e))
            if not failCreate:
                await session.commit()
                for o in createdObj:
                    await session.refresh(o)
            res = create_response(
                data={"status":statuses},
                meta={
                    "succeed": successCreate,
                    "failed": failCreate
                },
                status=status.error() if failCreate else status.success()
                )
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def update(
            self,
            pydanticModel,
            id,
            session: AsyncSession,
            whereClauseObject: Optional[BaseWhereClause] = None,
            **whereClause
        ):
        try:
            query = select(self.classModel)
            if id!=None:
                query = query.where(self.classModel.id==id)
            if whereClauseObject:
                query = whereClauseObject.applyWhereObject(query, whereClause)
            data = await session.execute(query)
            data = data.scalars().first()
            if not data:
                res = create_response(status=status.data_is_not_updated())
            else:
                await update_data(session, self.classModel, data, pydanticModel)
                res = create_response(status=status.success())
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def update_one(
            self,
            pydanticModel,
            session: AsyncSession,
            whereClauseObject: Optional[BaseWhereClause] = None,
            **whereClause
        ):
        try:
            query = select(self.classModel)
            for k, attr in pydanticModel.dict().items():
                if k in vars(self.classModel):
                    query = query.where(vars(self.classModel)[k]==attr)
            if whereClauseObject:
                query = whereClauseObject.applyWhereObject(query, whereClause)
            data = await session.execute(query)
            data = data.scalars().first()
            if not data:
                res = create_response(status=status.data_is_not_updated())
            else:
                await update_data(
                    session, self.classModel, data,
                    pydanticModel.__dict__[self.classModel.__tablename__]
                    )
                res = create_response(status=status.success())
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def update_many(
            self,
            pydanticModelCollection,
            reference_key,
            session: AsyncSession
        ):
        try:
            dataCollection = pydanticModelCollection.__dict__[self.classModel.__tablename__]
            statuses = []
            successUpdate = 0
            failUpdate = 0
            for data in dataCollection:
                try:                    
                    query = select(self.classModel)
                    query = self.where().applyWhereObject(
                        query, {reference_key: data.dict()[reference_key]}
                        )
                    obj = await session.execute(query)
                    obj = obj.scalars().first()
                    if not obj:
                        failUpdate += 1
                        statuses.append(status.data_is_not_updated())
                    else:
                        await update_data(session, self.classModel, obj, data)
                        successUpdate += 1
                        statuses.append(status.success())
                except Exception as e:
                    logger.error(str(e))
                    failUpdate += 1
                    statuses.append(status.error(e))
            res = create_response(
                data={"status": statuses},
                meta={
                    "succeed": successUpdate,
                    "failed": failUpdate
                },
                status=status.success()
                )
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

    async def delete(
            self,
            id: Optional[int],
            session: AsyncSession,
            whereClauseObject: Optional[BaseWhereClause] = None,
            **whereClause
        ):
        try:
            query = select(self.classModel)
            if id != None:
                query = query.where(self.classModel.id == id)
            if whereClauseObject:
                query = whereClauseObject.applyWhereObject(query, whereClause)
            data = await session.execute(query)
            data = data.scalars().all()
            if not data:
                res = create_response(status=status.data_is_not_exist())
            else:
                for d in data:
                    await session.delete(d)
                await session.commit()
                res = create_response(status=status.success())
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res
    
    async def delete_many(
            self,
            deleteParamsPydantic,
            session: AsyncSession
        ):
        try:
            statuses = []
            successDelete = 0
            failDelete = 0
            query = select(self.classModel)
            query = self.where().applyWhereObject(query, deleteParamsPydantic.dict())
            print(11111, query)
            datas = await session.execute(query)
            datas = datas.scalars().all()
            for data in datas:
                try:
                    if not data:
                        failDelete += 1
                        statuses.append(status.data_is_not_exist())
                    else:
                        await session.delete(data)
                        successDelete += 1
                        statuses.append(status.success())
                except Exception as e:
                    logger.error(e)
                    failDelete += 1
                    statuses.append(status.error(e))
            await session.commit()
            res = create_response(
                data={"status": statuses},
                meta={
                    "succeed": successDelete,
                    "failed": failDelete
                },
                status=status.success()
                )
        except Exception as e:
            logger.error(str(e))
            res = create_response(status=status.error(e))
        return res

def generate_pydantic_model(
        classModel: decl_api.DeclarativeMeta,
        modelName: str = "",
        exclude_attributes: Optional[List[Union[str, Column, InstrumentedAttribute]]] = [],
        include_attributes_default: Optional[Dict[str, Any]] = {},
        include_attributes_paramsType: Optional[
            Dict[str, Union[
                fastapi.Path, fastapi.Body, fastapi.Form, fastapi.Query, fastapi.Cookie, fastapi.Header
                ]]] = {},
        uniform_attributes_default: Optional[Any] = None,
        uniform_attributes_paramsType: Optional[Union[
            fastapi.Path, fastapi.Body, fastapi.Form, fastapi.Query, fastapi.Cookie, fastapi.Header
            ]] = None
    ):
    annots = get_annotation(classModel)
    for ex_at in exclude_attributes:
        if type(ex_at) != str:
            ex_at = ex_at.__str__().split(".")[1]
        if ex_at in annots:
            annots.pop(ex_at)
    for key, at_def in include_attributes_default.items():
        if key in annots:
            dataType, defVal = annots[key]
            annots[key] = (dataType, at_def)
    if uniform_attributes_paramsType:
        for key, an in annots.items():
            dataType, defVal = an
            if uniform_attributes_default:
                defVal = uniform_attributes_default
            try:
                if (
                        [
                            len(dataType.__args__) > 1,
                            type(None) in dataType.__args__,
                        ]
                    ):
                    annots[key] = (dataType, uniform_attributes_paramsType(default=defVal))
                else:
                    annots[key] = (dataType, uniform_attributes_paramsType(..., default=defVal))
            except:
                annots[key] = (dataType, uniform_attributes_paramsType(default=defVal))
    else:
        for key, at_ptype in include_attributes_paramsType.items():
            if key in annots:
                try:
                    dataType, defVal = annots[key]
                    if uniform_attributes_default:
                        defVal = uniform_attributes_default
                    if (
                            [
                                len(dataType.__args__) > 1,
                                type(None) in dataType.__args__,
                            ]
                        ):
                        if defVal:
                            annots[key] = (dataType, at_ptype(default=defVal))
                        else:
                            annots[key] = (dataType, at_ptype(...))
                    else:
                        annots[key] = (dataType, at_ptype(..., default=defVal))
                except:
                    annots[key] = (dataType, at_ptype(default=defVal))
    if not modelName: modelName = classModel.tablename+"Pydantic"
    ModelPydantic = create_model(modelName, **annots)
    return ModelPydantic

def get_annotation(classModel: decl_api.DeclarativeMeta):
    try:
        fields = [i for i in vars(classModel) if "_" not in [i[0], i[-1]]]
        keyValuePair = {}
        for f in fields:
            if "comparator" in classModel.__dict__[f].__dict__:
                if "column" in str(classModel.__dict__[f].__dict__["comparator"]).lower():
                    comp = classModel.__dict__[f].__dict__["comparator"]
                    if "VARCHAR" in str(comp.type):
                        if "enum_class" in comp.type.__dict__:
                            if comp.nullable:
                                defaultValue = comp.default.arg if comp.default else None
                                keyValuePair[f] = (Optional[comp.type.enum_class], defaultValue)
                            else:
                                defaultValue = comp.default.arg if comp.default else None
                                keyValuePair[f] = (comp.type.enum_class, defaultValue)
                        else:
                            if comp.nullable:
                                defaultValue = comp.default.arg if comp.default else None
                                keyValuePair[f] = (Optional[str], defaultValue)
                            else:
                                defaultValue = comp.default.arg if comp.default else None
                                keyValuePair[f] = (str, defaultValue)
                    elif "TEXT" in str(comp.type):
                        if comp.nullable:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (Optional[str], defaultValue)
                        else:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (str, defaultValue)
                    elif "BOOLEAN" in str(comp.type):
                        if comp.nullable:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (Optional[bool], defaultValue)
                        else:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (bool, defaultValue)
                    elif "INTEGER" in str(comp.type):
                        if comp.nullable:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (Optional[int], defaultValue)
                        else:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (int, defaultValue)
                    elif "FLOAT" in str(comp.type):
                        if comp.nullable:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (Optional[float], defaultValue)
                        else:
                            defaultValue = comp.default.arg if comp.default else None
                            keyValuePair[f] = (float, defaultValue)
                    elif "DATETIME" in str(comp.type):
                        if comp.nullable:
                            defaultValue = None
                            keyValuePair[f] = (Optional[datetime], defaultValue)
                        else:
                            defaultValue = None
                            keyValuePair[f] = (datetime, defaultValue)
        return keyValuePair
    except:
        return {}