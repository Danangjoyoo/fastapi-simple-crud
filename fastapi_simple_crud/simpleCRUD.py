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

from .routing import *


class RouterMap():
    """
    Router Mapping Class to define and simplify your router simple CRUD
    """
    __updated_routers = {}

    @classmethod
    def _get_variable(cls):
        return [cls.__dict__[v] for v in vars(cls) if type(cls.__dict__[v]) in RouterClasses]
    
    @classmethod
    def _get_key_value(cls):
        return {v: cls.__dict__[v] for v in vars(cls) if type(cls.__dict__[v]) in RouterClasses}

    @classmethod
    def _collect_simple_router(cls):
        allRouters = {}
        for c in cls.__subclasses__():
            for v in c._get_key_value().values():
                allRouters[v.tablename] = v
            if c.__subclasses__():
                allRouters.update(c._collect_simple_router())
        if cls == RouterMap:
            allRouters.update(RouterMap.__updated_routers)
        return allRouters
    
    @staticmethod
    def create_router_map_from_base(
            base: decl_api.DeclarativeMeta,
            base_prefix: str = "",
            extend: bool = False
        ):
        """
        Create All CRUD Automatically from SQLAlchemy declared base
        
        :params:
        - base -> SQLAlchemy declarative base
        - base_prefix -> Base prefix path for all endpoints in one router
        - extend -> Applying ExtendedRouter for more API
        """
        class AutoMap(RouterMap): pass
        targetRouter = ExtendedRouter if extend else SimpleRouter 
        for c in base.__subclasses__():
            setattr(
                AutoMap,
                c.__tablename__,                
                targetRouter(c, prefix=base_prefix+"/"+c.__tablename__, tags=[c.__tablename__])
                )
        return AutoMap
    
    @classmethod
    def update_map(cls, simple_router: SimpleRouterType):
        """
        Add your fastapi_simple_crud.SimpleRouter object to be generated outside of the router map
        """
        if cls == RouterMap:
            RouterMap.__updated_routers[simple_router.tablename] = simple_router
        else:
            setattr(cls, simple_router.tablename, simple_router)

    @classmethod
    def generate(
            cls,
            application: Optional[FastAPI] = None,
            session_getter: Optional[FunctionType] = None
        ):
        """
        Generate routers that have been defined using RouterMap
        
        :params
        - application -> FastAPI Application
        - session_getter -> SQLAlchemy AsyncSession Getter/yielder
        """
        if cls == RouterMap:
            return SimpleCRUDGenerator(application, session_getter, True)
        e = "RouterMap.generate() only able to be called from 'RouterMap' class"
        raise BaseException(e)


class SimpleCRUDGenerator():
    """
    Create CRUD Operation in a simple way.
    
    params:
    - application -> FastAPI Application
    - session_getter -> method to get the sqlalchemy session
    - autogenerate (bool) -> once instantiated, the base crud endpoints will be created
    """
    def __init__(
            self,
            application: Optional[FastAPI] = None,
            session_getter: Optional[FunctionType] = None, 
            autogenerate: bool = True
        ):
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

    def update_map(self, simple_router: SimpleRouterType):
        """
        Add your fastapi_simple_crud.SimpleRouter object to be generated outside of the router map
        """
        self.allRouters[simple_router.tablename] = simple_router

    def generate_router(
            self,
            application: Optional[FastAPI] = None,
            session_getter: Optional[FunctionType] = None
        ):
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