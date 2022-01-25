from fastapi import FastAPI, APIRouter, Depends, Request, Path
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

from .dependencies.utils import BaseCRUD
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
    
    def get_endpoint_kwargs(self):
        params = vars(self).copy()
        params.pop("enable")
        params.pop("modelPydantic")
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
        self.modelPydanticforCreate = self.generate_pydantic_model(modelName=self.tablename+"PydanticSimpleCreate")
        self.modelPydanticforUpdate = self.generate_pydantic_model(modelName=self.tablename+"PydanticSimpleUpdate", excluded_attributes=["id"])
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
        self.__get_session = None
    
    def set_the_get_session(self, method: FunctionType):
        self.__get_session = method

    def generate_pydantic_model(self, modelName: str = "", excluded_attributes=[]):
        annots = self.get_annotation()
        for ex_at in excluded_attributes:
            if ex_at in annots: annots.pop(ex_at)
        if not modelName: modelName = self.tablename+"Pydantic"
        ModelPydantic = create_model(modelName, **annots)
        return ModelPydantic
    
    def get_annotation(self):
        try:
            classModel = self.classModel
            fields = [i for i in vars(classModel) if "_" not in [i[0], i[-1]]]
            keyValuePair = {}
            for f in fields:
                if "comparator" in classModel.__dict__[f].__dict__:
                    if "column" in str(classModel.__dict__[f].__dict__["comparator"]).lower():
                        comp = classModel.__dict__[f].__dict__["comparator"]
                        if "VARCHAR" in str(comp.type):
                            if "enum_class" in comp.type.__dict__:
                                if comp.nullable:
                                    keyValuePair[f] = (Optional[comp.type.enum_class], None)
                                else:
                                    keyValuePair[f] = (comp.type.enum_class, None)                                    
                            else:
                                if comp.nullable:
                                    keyValuePair[f] = (Optional[str], None)
                                else:
                                    keyValuePair[f] = (str, None)
                        elif "TEXT" in str(comp.type):
                            if comp.nullable:
                                keyValuePair[f] = (Optional[str], None)
                            else:
                                keyValuePair[f] = (str, None)
                        elif "BOOLEAN" in str(comp.type):
                            if comp.nullable:
                                keyValuePair[f] = (Optional[bool], None)
                            else:
                                keyValuePair[f] = (bool, None)
                        elif "INTEGER" in str(comp.type):
                            if comp.nullable:
                                keyValuePair[f] = (Optional[int], None)
                            else:
                                keyValuePair[f] = (int, None)
                        elif "FLOAT" in str(comp.type):
                            if comp.nullable:
                                keyValuePair[f] = (Optional[float], None)
                            else:
                                keyValuePair[f] = (float, None)
                        elif "DATETIME" in str(comp.type):
                            if comp.nullable:
                                keyValuePair[f] = (Optional[datetime], None)
                            else:
                                keyValuePair[f] = (datetime, None)
            return keyValuePair
        except:
            return {}

    def _setup_crud(self):
        if self.crud_create.enable:
            kargs = self.crud_create.get_endpoint_kwargs()
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
                    session: AsyncSession = Depends(self.__get_session)
                ):
                return await self.crud.create(modelPydantic, session)
        
        if self.crud_read.enable:
            kargs = self.crud_read.get_endpoint_kwargs()
            if not kargs["name"]:
                kargs["name"] = "read "+self.tablename
            @self.get(**kargs)
            async def base_get(
                    request: Request,
                    getParams = Depends(CommonQueryGetter),
                    session: AsyncSession = Depends(self.__get_session)
                ):
                return await self.crud.read(getParams, session)

        if self.crud_update.enable:
            kargs = self.crud_update.get_endpoint_kwargs()
            if not kargs["name"]:
                kargs["name"] = "update "+self.tablename
            if self.crud_update.modelPydantic:
                modelPydantic_ = self.crud_update.modelPydantic
            else:
                modelPydantic_ = self.modelPydanticforUpdate
            @self.put(**kargs)
            async def base_put(
                    request: Request,
                    modelPydantic: modelPydantic_,
                    id: int = Path(...,min=1),
                    session: AsyncSession = Depends(self.__get_session)
                ):
                return await self.crud.update(modelPydantic, id, session)

        if self.crud_delete.enable:
            kargs = self.crud_delete.get_endpoint_kwargs()
            if not kargs["name"]:
                kargs["name"] = "delete "+self.tablename
            @self.delete(**kargs)
            async def base_delete(
                    request: Request,
                    id: int = Path(...,min=1),
                    session: AsyncSession = Depends(self.__get_session)
                ):
                return await self.crud.delete(id, session)


class RouterMap():
    """
    Router Mapping Class to define and simplify your router simple CRUD
    """
    @classmethod
    def _get_variable(cls):
        return [cls.__dict__[v] for v in vars(cls) if type(cls.__dict__[v]) == SimpleRouter]
    
    @classmethod
    def _get_key_value(cls):
        return {v: cls.__dict__[v] for v in vars(cls) if type(cls.__dict__[v]) == SimpleRouter}

    @classmethod
    def _collect_simple_router(cls):
        allRouters = {}
        for c in cls.__subclasses__():
            for v in c._get_key_value().values():
                allRouters[v.tablename] = v
            if c.__subclasses__():
                allRouters.update(c._collect_simple_router())                
        return allRouters
    
    @staticmethod
    def create_router_map_from_base(base: decl_api.DeclarativeMeta, base_prefix: str = ""):
        """
        Create All CRUD Automatically from SQLAlchemy declared base
        """
        class AutoMap(RouterMap): pass
        for c in base.__subclasses__():
            setattr(
                AutoMap,
                c.__tablename__,                
                SimpleRouter(c, prefix=base_prefix+"/"+c.__tablename__, tags=[c.__tablename__])
                )
        return AutoMap
        

class SimpleCRUDGenerator():
    """
    Create CRUD Operation in a simple way.
    
    params:
    - application -> FastAPI Application
    - session_getter -> method to get the sqlalchemy session
    - autogenerate (bool) -> once instantiated, the base crud endpoints will be created
    """
    def __init__(self, application: Optional[FastAPI] = None, session_getter: Optional[FunctionType] = None, autogenerate: bool = True):
        self.app = application
        self.allRouters = RouterMap._collect_simple_router()
        self.session_getter = session_getter
        if not all([application, session_getter]): autogenerate = False
        if autogenerate: self.generate_router()
    
    def set_application(self, application: FastAPI):
        """
        Set your FastAPI object application
        """
        self.app = application
    
    def set_session_getter(self, session_getter: FunctionType):
        """
        Set your session getter for SQLAlchemy
        """
        self.session_getter = session_getter

    def add_simple_router(self, simple_router: SimpleRouter):
        """
        Add your fastapi_simple_crud.SimpleRouter object to be generated outside of the router map
        """
        self.allRouters[simple_router.tablename] = simple_router

    def generate_router(self, application: Optional[FastAPI] = None, session_getter: Optional[FunctionType] = None):
        """
        Generate defined router map
        """
        if application: self.set_application(application)
        if session_getter: self.set_session_getter(session_getter)
        if all([self.app, self.session_getter]):
            for tag in sorted(self.allRouters):
                router = self.allRouters[tag]
                router.set_the_get_session(self.session_getter)
                router._setup_crud()
                self.app.include_router(router)