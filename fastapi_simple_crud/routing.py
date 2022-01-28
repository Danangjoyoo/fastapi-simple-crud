from fastapi import FastAPI, APIRouter, Depends, Request, Path, Query, Body
from fastapi.encoders import SetIntStr, DictIntStrAny
from fastapi.routing import APIRoute
from fastapi.datastructures import Default
from pydantic import BaseConfig, BaseModel, create_model
from pydantic.fields import ModelField
from starlette.routing import BaseRoute
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp
from typing import Optional, List, Sequence, Type, Any, Callable, Union, Dict
from sqlalchemy.orm import decl_api
from sqlalchemy.ext.asyncio import AsyncSession
from types import FunctionType
from datetime import datetime

from .dependencies.utils import BaseCRUD, generate_pydantic_model
from .dependencies.utility import CommonQueryGetter


class SimpleEndpoint:
    def __init__(self, 
            path: str = "",
            enable: bool = True,
            response_model: Optional[Type[Any]] = None,
            status_code: Optional[int] = None,
            tags: Optional[List[str]] = None,
            dependencies: Optional[Sequence[Depends]] = None,
            summary: Optional[str] = None,
            description: Optional[str] = None,
            response_description: str = "Successful Response",
            responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
            deprecated: Optional[bool] = None,
            operation_id: Optional[str] = None,
            response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
            response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
            response_model_by_alias: bool = True,
            response_model_exclude_unset: bool = False,
            response_model_exclude_defaults: bool = False,
            response_model_exclude_none: bool = False,
            include_in_schema: bool = True,
            response_class: Type[Response] = Default(JSONResponse),
            name: Optional[str] = None,
            callbacks: Optional[List[BaseRoute]] = None,
            openapi_extra: Optional[Dict[str, Any]] = None,
            pydantic_model: Optional[BaseModel] = None
        ):
        self.enable = enable
        self.path = path
        self.response_model = response_model
        self.status_code = status_code
        self.tags = tags
        self.dependencies = dependencies
        self.summary = summary
        self.description = description
        self.response_description = response_description
        self.responses = responses
        self.deprecated = deprecated
        self.operation_id = operation_id
        self.response_model_include = response_model_include
        self.response_model_exclude = response_model_exclude
        self.response_model_by_alias = response_model_by_alias
        self.response_model_exclude_unset = response_model_exclude_unset
        self.response_model_exclude_defaults = response_model_exclude_defaults
        self.response_model_exclude_none = response_model_exclude_none
        self.include_in_schema = include_in_schema
        self.response_class = response_class
        self.name = name
        self.callbacks = callbacks
        self.openapi_extra = openapi_extra
        self.modelPydantic = pydantic_model
    
    def get_endpoint_kwargs(self, exclude_attributes: Optional[List[str]]=[]):
        params = vars(self).copy()
        for key in exclude_attributes:
            params.pop(key)
        return params    


class SimpleRouter(APIRouter):
    """
    Simple Router Class to define a router for SimpleCRUDGenerator
    """
    def __init__(
            self,
            classModel: decl_api.DeclarativeMeta,
            *,
            prefix: str = "",
            tags: Optional[List[str]] = None,
            dependencies: Optional[Sequence[Depends]] = None,
            default_response_class: Type[Response] = Default(JSONResponse),
            responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
            callbacks: Optional[List[BaseRoute]] = None,
            routes: Optional[List[BaseRoute]] = None,
            redirect_slashes: bool = True,
            default: Optional[ASGIApp] = None,
            dependency_overrides_provider: Optional[Any] = None,
            route_class: Type[APIRoute] = APIRoute,
            on_startup: Optional[Sequence[Callable[[], Any]]] = None,
            on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
            deprecated: Optional[bool] = None,
            include_in_schema: bool = True,
            crud_create: Union[SimpleEndpoint, bool, None] = True,
            crud_read: Union[SimpleEndpoint, bool, None] = True,
            crud_update: Union[SimpleEndpoint, bool, None] = True,
            crud_delete: Union[SimpleEndpoint, bool, None] = True,
            disable_simple_crud: bool = False
        ):
        self.classModel = classModel
        self.tablename = classModel.__tablename__
        self.modelPydanticforCreate = generate_pydantic_model(self.classModel, modelName=self.tablename+"PydanticSimpleCreate")
        self.modelPydanticforUpdate = generate_pydantic_model(self.classModel, modelName=self.tablename+"PydanticSimpleUpdate", exclude_attributes=["id"])
        self.crud = BaseCRUD(classModel)
        if not tags: tags = [self.tablename]
        if not prefix: prefix = f"/{self.tablename}"
        super().__init__(
                prefix=prefix,
                tags=tags,
                dependencies=dependencies,
                default_response_class=default_response_class,
                responses=responses,
                callbacks=callbacks,
                routes=routes,
                redirect_slashes=redirect_slashes,
                default=default,
                dependency_overrides_provider=dependency_overrides_provider,
                route_class=route_class,
                on_startup=on_startup,
                on_shutdown=on_shutdown,
                deprecated=deprecated,
                include_in_schema=include_in_schema)
        if disable_simple_crud:
            crud_create = None
            crud_read = None
            crud_update = None
            crud_delete = None
        if type(crud_create) == SimpleEndpoint:
            self.crud_create = crud_create
        else:
            if crud_create:
                self.crud_create = SimpleEndpoint(enable=True)
            else:
                self.crud_create = SimpleEndpoint(enable=False)
        if type(crud_read) == SimpleEndpoint:
            self.crud_read = crud_read
        else:
            if crud_read:
                self.crud_read = SimpleEndpoint(enable=True)
            else:
                self.crud_read = SimpleEndpoint(enable=False)
        if type(crud_update) == SimpleEndpoint:
            self.crud_update = crud_update
        else:
            if crud_update:
                self.crud_update = SimpleEndpoint(path="/{id}", enable=True)
            else:
                self.crud_update = SimpleEndpoint(enable=False)
        if type(crud_delete) == SimpleEndpoint:
            self.crud_delete = crud_delete
        else:
            if crud_delete:
                self.crud_delete = SimpleEndpoint(path="/{id}", enable=True)
            else:
                self.crud_delete = SimpleEndpoint(enable=False)
        self._get_session = None
    
    def set_the_get_session(self, method: FunctionType):
        self._get_session = method
        
    def _setup_crud(self):
        if self.crud_create.enable:
            kargs = self.crud_create.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "create "+self.tablename
            if self.crud_create.modelPydantic:
                modelPydantic_ = self.crud_create.modelPydantic
            else:
                modelPydantic_ = self.modelPydanticforCreate
            @self.post(**kargs)
            async def base_post(
                    request: Request,
                    modelPydantic: modelPydantic_,
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.create(modelPydantic, session)
        
        if self.crud_read.enable:
            # kargs = self.crud_read.get_endpoint_kwargs(
            #     exclude_attributes=["enable","modelPydantic"]
            #     )
            # if not kargs["name"]:
            #     kargs["name"] = "read "+self.tablename
            # @self.get(**kargs)
            # async def base_get(
            #         request: Request,
            #         getParams = Depends(CommonQueryGetter),
            #         session: AsyncSession = Depends(self._get_session)
            #     ):
            #     return await self.crud.read(getParams, session)
            kargs = self.crud_read.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "read many "+self.tablename
            if self.crud_read.modelPydantic:
                modelPydantic_ = self.crud_read.modelPydantic
            else:
                modelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleReadMany",
                    uniform_attributes_paramsType=Query
                )
            @self.get(**kargs)
            async def base_get_many(
                    request: Request,
                    readParams = Depends(modelPydantic_),
                    getParams = Depends(CommonQueryGetter),
                    session: AsyncSession = Depends(self._get_session)
                ):
                wc = self.crud.where(**readParams.dict())
                return await self.crud.read_many(getParams, session, wc)

        if self.crud_update.enable:
            # kargs = self.crud_update.get_endpoint_kwargs(
            #     exclude_attributes=["enable","modelPydantic"]
            #     )
            # if not kargs["name"]:
            #     kargs["name"] = "update "+self.tablename
            # if self.crud_update.modelPydantic:
            #     modelPydantic_ = self.crud_update.modelPydantic
            # else:
            #     modelPydantic_ = self.modelPydanticforUpdate
            # @self.put(**kargs)
            # async def base_put(
            #         request: Request,
            #         modelPydantic: modelPydantic_,
            #         id: int = Path(...,min=1),
            #         session: AsyncSession = Depends(self._get_session)
            #     ):
            #     return await self.crud.update(modelPydantic, id, session)
            kargs = self.crud_update.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "update one "+self.tablename
            if self.crud_update.modelPydantic:
                modelPydantic_ = self.crud_update.modelPydantic
            else:
                premodelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleUpdateOne",
                    exclude_attributes=["id"],
                )
                modelPydantic_ = create_model(
                    self.tablename+"PydanticSimpleUpdateOnePacked",
                    **{
                        "id": (int, Path(...)),
                        self.tablename: (premodelPydantic_, Body(...))
                    }
                )
            @self.put(**kargs)
            async def base_put(
                    request: Request,
                    modelPydantic: modelPydantic_ = Depends(),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.update_one(modelPydantic, session)

        if self.crud_delete.enable:
            kargs = self.crud_delete.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "delete "+self.tablename
            @self.delete(**kargs)
            async def base_delete(
                    request: Request,
                    id: int = Path(...,min=1),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.delete(id, session)


class ExtendedRouter(SimpleRouter):
    """
    Extended Version of Simple Router.

    Provide the following API:
    - create one
    - create many
    - read one
    - read many
    - update one
    - update many
    - delete one
    - delete many
    """
    def __init__(
            self,
            classModel: decl_api.DeclarativeMeta,
            *,
            prefix: str = "",
            tags: Optional[List[str]] = None,
            dependencies: Optional[Sequence[Depends]] = None,
            default_response_class: Type[Response] = Default(JSONResponse),
            responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
            callbacks: Optional[List[BaseRoute]] = None,
            routes: Optional[List[BaseRoute]] = None,
            redirect_slashes: bool = True,
            default: Optional[ASGIApp] = None,
            dependency_overrides_provider: Optional[Any] = None,
            route_class: Type[APIRoute] = APIRoute,
            on_startup: Optional[Sequence[Callable[[], Any]]] = None,
            on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
            deprecated: Optional[bool] = None,
            include_in_schema: bool = True,
            create_one: Union[SimpleEndpoint, bool, None] = True,
            create_many: Union[SimpleEndpoint, bool, None] = True,
            read_one: Union[SimpleEndpoint, bool, None] = True,
            read_many: Union[SimpleEndpoint, bool, None] = True,
            # read_many_like: Union[SimpleEndpoint, bool, None] = True,
            update_one: Union[SimpleEndpoint, bool, None] = True,
            update_many: Union[SimpleEndpoint, bool, None] = True,
            delete_one: Union[SimpleEndpoint, bool, None] = True,
            delete_many: Union[SimpleEndpoint, bool, None] = True,
            disable_extended_crud: bool = False
        ):
        super().__init__(
                classModel=classModel,
                prefix=prefix,
                tags=tags,
                dependencies=dependencies,
                default_response_class=default_response_class,
                responses=responses,
                callbacks=callbacks,
                routes=routes,
                redirect_slashes=redirect_slashes,
                default=default,
                dependency_overrides_provider=dependency_overrides_provider,
                route_class=route_class,
                on_startup=on_startup,
                on_shutdown=on_shutdown,
                deprecated=deprecated,
                include_in_schema=include_in_schema,
                disable_simple_crud=True)
   
        if disable_extended_crud:
            create_one = None
            create_many = None
            read_one = None
            read_many = None
            update_one = None
            update_many = None
            delete_one = None
            delete_many = None

        # create one
        if type(create_one) == SimpleEndpoint:
            self.create_one = create_one
        else:
            if create_one:
                self.create_one = SimpleEndpoint(path="/one",enable=True)
            else:
                self.create_one = SimpleEndpoint(enable=False)

        # create many
        if type(create_many) == SimpleEndpoint:
            self.create_many = create_many
        else:
            if create_many:
                self.create_many = SimpleEndpoint(path="",enable=True)
            else:
                self.create_many = SimpleEndpoint(enable=False)

        # read one
        if type(read_one) == SimpleEndpoint:
            self.read_one = read_one
        else:
            if read_one:
                self.read_one = SimpleEndpoint(path="/one", enable=True)
            else:
                self.read_one = SimpleEndpoint(enable=False)
        
        # read many
        if type(read_many) == SimpleEndpoint:
            self.read_many = read_many
        else:
            if read_many:
                self.read_many = SimpleEndpoint(path="", enable=True)
            else:
                self.read_many = SimpleEndpoint(enable=False)
        
        # # read many like
        # if type(read_paginate) == SimpleEndpoint:
        #     self.read_paginate = read_paginate
        # else:
        #     if read_paginate:
        #         self.read_paginate = SimpleEndpoint(path="/like", enable=True)
        #     else:
        #         self.read_paginate = SimpleEndpoint(enable=False)
        
        # update one
        if type(update_one) == SimpleEndpoint:
            self.update_one = update_one
        else:
            if update_one:
                self.update_one = SimpleEndpoint(path="/{id}", enable=True)
            else:
                self.update_one = SimpleEndpoint(enable=False)
        
        # update many
        if type(update_many) == SimpleEndpoint:
            self.update_many = update_many
        else:
            if update_many:
                self.update_many = SimpleEndpoint(path="", enable=True)
            else:
                self.update_many = SimpleEndpoint(enable=False)

        # delete one
        if type(delete_one) == SimpleEndpoint:
            self.delete_one = delete_one
        else:
            if delete_one:
                self.delete_one = SimpleEndpoint(path="/{id}", enable=True)
            else:
                self.delete_one = SimpleEndpoint(enable=False)
        
        # delete many
        if type(delete_many) == SimpleEndpoint:
            self.delete_many = delete_many
        else:
            if delete_many:
                self.delete_many = SimpleEndpoint(path="", enable=True)
            else:
                self.delete_many = SimpleEndpoint(enable=False)
    
    def _setup_crud(self):
        if self.create_one.enable:
            kargs = self.create_one.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "create one "+self.tablename
            if self.create_one.modelPydantic:
                modelPydantic_ = self.create_one.modelPydantic
            else:
                modelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleCreateOne"
                )
            @self.post(**kargs)
            async def base_post_one(
                    request: Request,
                    modelPydantic: modelPydantic_,
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.create(modelPydantic, session)

        if self.create_many.enable:
            kargs = self.create_many.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "create many "+self.tablename
            if self.create_many.modelPydantic:
                modelPydantic_ = self.create_many.modelPydantic
            else:
                modelPydantic_ = create_model(
                    self.tablename+"PydanticSimpleCreateMany",
                    **{self.tablename: (
                        Optional[
                            List[
                                generate_pydantic_model(
                                    classModel=self.classModel,
                                    modelName=self.tablename+"PydanticSimpleCreateOneForMany"
                                    )
                                ]
                            ],
                        None
                        )
                    }
                )
            @self.post(**kargs)
            async def base_post_many(
                    request: Request,
                    modelPydantic: modelPydantic_,
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.create_many(modelPydantic, session)

        if self.read_one.enable:
            kargs = self.read_one.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "read one "+self.tablename
            if self.read_one.modelPydantic:
                modelPydantic_ = self.read_one.modelPydantic
            else:
                modelPydantic_ = create_model(
                    self.tablename+"PydanticSimpleReadOne", id=(int, Query(...))
                    )
            @self.get(**kargs)
            async def base_get_one(
                    request: Request,
                    modelPydantic_ = Depends(modelPydantic_),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.read_one(modelPydantic_, session)
        
        if self.read_many.enable:
            kargs = self.read_many.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "read many "+self.tablename
            if self.read_many.modelPydantic:
                modelPydantic_ = self.read_many.modelPydantic
            else:
                modelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleReadMany",
                    uniform_attributes_paramsType=Query
                )
            @self.get(**kargs)
            async def base_get_many(
                    request: Request,
                    readParams = Depends(modelPydantic_),
                    getParams = Depends(CommonQueryGetter),
                    session: AsyncSession = Depends(self._get_session)
                ):
                wc = self.crud.where(**readParams.dict())
                return await self.crud.read_many(getParams, session, wc)

        # if self.read_paginate.enable:
        #     kargs = self.read_paginate.get_endpoint_kwargs(
        #         exclude_attributes=["enable","modelPydantic"]
        #         )
        #     if not kargs["name"]:
        #         kargs["name"] = "read paginate "+self.tablename
        #     @self.get(**kargs)
        #     async def base_get_paginate(
        #             request: Request,
        #             getParams = Depends(CommonQueryGetter),
        #             session: AsyncSession = Depends(self._get_session)
        #         ):
        #         return await self.crud.read(getParams, session)

        if self.update_one.enable:
            kargs = self.update_one.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "update one "+self.tablename
            if self.update_one.modelPydantic:
                modelPydantic_ = self.update_one.modelPydantic
            else:
                premodelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleUpdateOne",
                    exclude_attributes=["id"],
                )
                modelPydantic_ = create_model(
                    self.tablename+"PydanticSimpleUpdateOnePacked",
                    **{
                        "id": (int, Path(...)),
                        self.tablename: (premodelPydantic_, Body(...))
                    }
                )
            @self.put(**kargs)
            async def base_put_one(
                    request: Request,
                    modelPydantic: modelPydantic_ = Depends(),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.update_one(modelPydantic, session)
        
        if self.update_many.enable:
            kargs = self.update_many.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "update many "+self.tablename
            if self.update_many.modelPydantic:
                modelPydantic_ = self.update_many.modelPydantic
            else:
                modelPydantic_ = create_model(
                    self.tablename+"PydanticSimpleUpdateMany",
                    **{self.tablename: (Optional[List[
                        generate_pydantic_model(
                            classModel=self.classModel,
                            modelName=self.tablename+"PydanticSimpleUpdateOneWithID"
                        )]], None)}
                )
            @self.put(**kargs)
            async def base_put_many(
                    request: Request,
                    pydanticModelCollection: modelPydantic_,
                    reference_key: str = Query(
                        ...,
                        description="Put your reference key that will be used to refer your data and won't be updated"
                        ),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.update_many(reference_key, pydanticModelCollection, session)

        if self.delete_one.enable:
            kargs = self.delete_one.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "delete one "+self.tablename
            @self.delete(**kargs)
            async def base_delete_one(
                    request: Request,
                    id: int = Path(...,min=1),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.delete(id, session)
        
        if self.delete_many.enable:
            kargs = self.delete_many.get_endpoint_kwargs(
                exclude_attributes=["enable","modelPydantic"]
                )
            if not kargs["name"]:
                kargs["name"] = "delete many "+self.tablename
            if self.delete_many.modelPydantic:
                modelPydantic_ = self.delete_many.modelPydantic
            else:
                modelPydantic_ = generate_pydantic_model(
                    classModel=self.classModel,
                    modelName=self.tablename+"PydanticSimpleDeleteMany",
                    uniform_attributes_paramsType=Query
                )
            @self.delete(**kargs)
            async def base_delete_many(
                    request: Request,
                    deleteParams = Depends(modelPydantic_),
                    session: AsyncSession = Depends(self._get_session)
                ):
                return await self.crud.delete_many(deleteParams, session)


RouterClasses = [SimpleRouter, ExtendedRouter]
SimpleRouterType = Union[SimpleRouter, ExtendedRouter]