# FastAPI Simple CRUD Generator
[![Downloads](https://static.pepy.tech/personalized-badge/fastapi-simple-crud?period=total&units=international_system&left_color=black&right_color=orange&left_text=Downloads)](https://pepy.tech/project/fastapi-simple-crud)

## Repository
- [ ] [GITHUB](https://github.com/Danangjoyoo/fastapi-simple-crud)

## Installation
```
pip install fastapi-simple-crud
```

## Description
A package to generate CRUD routers and API in a very simple way. Based on SQLAlchemy asynchronous operation and schema.

## Changelogs
- v0.0
    - First Upload
- v0.1:
    - Added `ExtendedRouter`
    - Bugs fix
    - v0.1.4 :
        - using `disable_crud` for both `SimpleRouter()` and `ExtendedRouter()` (previously `disable_simple_crud` and `disable_extended_crud` arguments)
    - v0.1.5 :
        - Auto Generated PydanticModel from both `SimpleRouter()` and `ExtendedRouter()` be accessed from their object
    - v0.1.6 :
        - `RouterMap.update_map()` can be used to update `ExtendedRouter()`

## How to use ?
```
from fastapi import FastAPI
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from fastapi_simple_crud import RouterMap

engine = create_async_engine("sqlite+aiosqlite:///./test.db", echo=True, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

class Country(Base):
    __tablename__ = "country"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)

class President(Base):
    __tablename__ = "president"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    country_id = Column(Integer, ForeignKey("country.id"))
    country = relationship("Country")

class People(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    country_id = Column(Integer, ForeignKey("country.id"))
    country = relationship("Country")

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


## ULTRA SIMPLE OH MY GOD!

MyMap = RouterMap.create_router_map_from_base(base=Base)

RouterMap.generate(app, get_session)
```

## Results
- your endpoints
    - ![alt text](https://raw.githubusercontent.com/Danangjoyoo/fastapi-simple-crud/main/images/endpoint_example1.png)
- your pydantic schema
    - ![alt text](https://raw.githubusercontent.com/Danangjoyoo/fastapi-simple-crud/main/images/schema_example1.png)

## Example 1b : Too few for you? Relax. We have the Extended Version
simply set the `extend` parameter to `True` then you got the fully extended version
```
## ULTRA SIMPLE OH MY GOD!

RouterMap.create_router_map_from_base(Base, base_prefix="/v1", extend=True)

RouterMap.generate(app, get_session)
```
- your extended endpoints
    - ![alt text](https://raw.githubusercontent.com/Danangjoyoo/fastapi-simple-crud/main/images/endpoint_example2.png)

---
## Using `RouterMap` superclass
### Simple usage
```
class MyMap(RouterMap):
    country = SimpleRouter(Country)
    president = SimpleRouter(President)
    people = ExtendedRouter(People)

```

### Additional usage
```
from fastapi_simple_crud import SimpleCRUDGenerator, RouterMap, SimpleRouter, SimpleEndpoint

## ULTRA SIMPLE OH MY GOD!

class MyPresidentPydantic(BaseModel):
    name: int

class MyMap(RouterMap):
    country = SimpleRouter(Country, prefix="/v1/country")
    president = SimpleRouter(President, prefix="/v1/president",
        crud_update=None,
        crud_create=SimpleEndpoint(pydantic_model=MyPresidentPydantic),
        crud_read=SimpleEndpoint("/custom_read"))

RouterMap.generate(app, get_session)
```
- This example show how to use `RouterMap` as a superclass
- You could disable the API generation by simply passing between these keyword arguments to `None` in the `SimpleRouter` definition:
  - `crud_create`
  - `crud_read`
  - `crud_update`
  - `crud_delete`
  - `disable_crud` (set this to `True` this will forcely disable all API generation)
- Only your defined router mapping inside you router map (in above example is `MyMap` class) will be generated. From the example, `People` router is not exist.
- `SimpleEndpoint()` refers to your HTTP method definition (GET/POST/PUT/DELETE) in the API decorator (ex: `@router.get()`, etc.)

### `RouterMap` with `ExtendedRouter()`
```
from fastapi_simple_crud import SimpleCRUDGenerator, RouterMap, ExtendedRouter, SimpleEndpoint

## ULTRA SIMPLE OH MY GOD!

class MyPresidentPydantic(BaseModel):
    name: int

class MyMap(RouterMap):
    country = ExtendedRouter(Country, prefix="/v1/country")
    president = ExtendedRouter(President, prefix="/v1/president",
        read_one=None,
        read_many=SimpleEndpoint("/custom_read")),
        update_one=SimpleEndpoint(pydantic_model=MyPresidentPydantic)

RouterMap.generate(app, get_session)
```
- You could disable the API generation by simply passing between these keyword arguments to `None` in the `ExtendedRouter` definition:
  - `create_one`
  - `create_many`
  - `read_one`
  - `read_many`
  - `update_one`
  - `update_many`
  - `delete_one`
  - `delete_many`
  - `disable_crud` (set this to `True` this will forcely disable all API generation)

---
## Add Your Custom API
```
from fastapi import Depends
from sqlalchemy import select
from fastapi_simple_crud import SimpleCRUDGenerator, RouterMap, SimpleRouter, SimpleEndpoint

## ULTRA SIMPLE OH MY GOD!

class MyPresidentPydantic(BaseModel):
    name: int

class MyMap(RouterMap):
    country = SimpleRouter(Country, prefix="/v1/country", crud_read=None)
    president = SimpleRouter(President, prefix="/v1/president")

@MyMap.country.get("/custom_read")
async def get_country(id: int, session: AsyncSession = Depends(get_session)):
    query = select(Country).where(Country.id==id)
    data = await session.execute(query)
    data = data.scalars().first()
    return data

RouterMap.generate(app, get_session)
```
- You could use your router from the your router map as shown above
---
## Disabling Some Routers
```
from fastapi_simple_crud import SimpleCRUDGenerator, RouterMap, SimpleRouter, SimpleEndpoint

## ULTRA SIMPLE OH MY GOD!

MyMap = RouterMap.create_router_map_from_base(base=Base)

## you want to remove people from autogeneration

class NewMap(MyMap):
    people = SimpleRouter(People, disable_crud=True)

RouterMap.generate(app, get_session)
```
or inherit from the `RouterMap`
```
class NewMap(RouterMap):
    people = SimpleRouter(People, disable_crud=True)
```
or simply update from the `RouterMap`
```
people = SimpleRouter(People, disable_crud=True)
RouterMap.update_map(people)
```
or from the `MyMap`
```
MyMap.update_map(people)
```
---
## Change Router Type
You can override `ExtendedRouter` with `SimpleRouter` and vice versa.
```
class NewMap(RouterMap):
    people = SimpleRouter(People)

class NewMap2(RouterMap):
    people = ExtendedRouter(People)
```
---
## Add your custom API from `RouterMap.create_router_map_from_base()`
```
from fastapi import Depends
from sqlalchemy import select
from fastapi_simple_crud import SimpleCRUDGenerator, RouterMap, SimpleRouter, SimpleEndpoint

class Country(Base):
    __tablename__ = "country"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)

## ULTRA SIMPLE OH MY GOD!

MyMap = RouterMap.create_router_map_from_base(base=Base)

## use your tablename to get the router attribute from the created router map
## RouterMap in default will automatically mapped your router with its tablename

@MyMap.country.get("/custom_read")
async def get_country(id: int, session: AsyncSession = Depends(get_session)):
    query = select(Country).where(Country.id==id)
    data = await session.execute(query)
    data = data.scalars().first()
    return data

RouterMap.generate(app, get_session)
```
- Use your tablename to get the router attribute from the created router map (in above is `MyMap`)
- `RouterMap` in default will automatically mapped your router with its tablename (in above `Country` tablename is `country`)

---
## Want to use your generated pydantic?
```
class MyMap(RouterMap):
    country = SimpleRouter(Country)
    president = SimpleRouter(President)
    people = ExtendedRouter(People)

## here you go
countryCreateOnePydanticModel = MyMap.country.create_one.pydanticModel
```
---
## Want to generate your own pydantic from SQLAlchemy schema?
for example we have this class
```
class People(Base):
    __tablename__ = "people"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(Integer)
    country_id = Column(Integer, ForeignKey("country.id"))
    country = relationship("Country")
    isAlive = Column(Boolean)
```
then simply put in to with `generate_pydantic_model()`
```
from fastapi import Query
from fastapi_simple_crud.dependencies.utils import generate_pydantic_model

myPeoplePydantic = generate_pydantic_model(People, modelName="myPeoplePydantic")
```
or with some params..
```
myPeoplePydantic = generate_pydantic_model(
            classModel=People,
            modelName="myPeoplePydantic",
            exclude_attributes=["id"],
            include_attributes_default={"isAlive": True},
            include_attributes_paramsType={"isAlive": Query},
        )
```
the code above will generate `People` pydantic model without `id` attribute

the available params are:
- `classModel` >> your SQLAlchemy Model Schema Class
- `modelName` >> your pydantic model name
- `exclude_attributes` >> put the attributes you dont want inside your pydanticModel (it will copy all relatied attributes from the SQLAlchemy schema)
- `include_attributes_default` >> set your attributes default params
- `include_attributes_paramsType` >> set your attributes default params
- `uniform_attributes_default` >> override all default value to uniform
- `uniform_attributes_paramsType` >> override all params type to uniform