import logging

logger = logging.getLogger()

# import logging, os, time, io
# from typing import List

# class CustomFilter(logging.Filter):
#     def __init__(self,logFormat,levels=[10,20,30,40,50],**kargs):
#         self.levels = levels
#         self._unapplied = ["_logFormat","_unapplied","filter","_applyAttr"]
#         self._logFormat = logFormat
#         if kargs:
#             for key in kargs:
#                 if not key in self.__dict__:
#                     setattr(self, key, kargs[key])

#     def _applyAttr(self, targetObject):
#         for attr, value in vars(self).items():
#             if (attr not in targetObject.__dict__) and (attr not in self._unapplied):
#                 setattr(targetObject, attr, value)
    
#     def _setLevels(self, *levels):
#         self.levels = levels

#     def filter(self, record):
#         self._applyAttr(record)
#         return record.levelno in self.levels

# class Streamer(logging.StreamHandler):
#     def __init__(self, filterObject):
#         super(Streamer, self).__init__()
#         self._formatter = logging.Formatter(filterObject._logFormat)
#         self.setFormatter(self._formatter)
#         self.addFilter(filterObject)

# class CustomLogger(logging.getLoggerClass()):
#     def __init__(self, name: str, disable: bool, filterObject: CustomFilter):
#         super(CustomLogger, self).__init__(name, 0)
#         self._streamer = Streamer(filterObject)
#         self.addHandler(self._streamer)
#         self.disabled = bool(disable)
#         self._filter = filterObject
    
#     def disable(self): 
#         self.disabled = True

#     def enable(self): 
#         self.disabled = False

#     def setLevels(self, levels: List[int]):
#         self._filter.levels = levels



# # globalFilter = CustomFilter(logFormat='[%(asctime)s][%(levelname)s] %(message)s', levels=Logger.levels)
# globalFilter = CustomFilter(
#     logFormat='[%(asctime)s][%(filename)s][%(levelname)s][line:%(lineno)s] - %(message)s'
#     )
# logger = CustomLogger(
#     name = "fastapi-simple-crud",
#     disable = False,
#     filterObject = globalFilter)

# """
# ## implementation examples
# # mock aja
# os.environ["SERVICE_NAME"] = "merchant-management"
# os.environ["LEVEL"] = "DEBUG"
# os.environ["LOG_DISABLE"] = "false"
# os.environ["ADMIN_SERVICE_NAME"] = "admin"
# os.environ["ADMIN_LEVEL"] = "DEBUG"
# os.environ["ADMIN_LOG_DISABLE"] = "false"


# # admin logger
# adminFilter = CustomFilter(
#         logFormat='%(asctime)s - %(name)s - %(filename)s - %(levelname)s line:%(lineno)s - %(user)s - %(status)s - %(message)s',
#         user="danang", status="mantap")

# adminLogger = CustomLogger(
#     name = os.getenv("ADMIN_SERVICE_NAME"),
#     level = os.getenv("ADMIN_LEVEL"),
#     disable = os.getenv("ADMIN_LOG_DISABLE") == "true",
#     filterObject = adminFilter)

# # general logger
# generalFilter = CustomFilter(
#         logFormat='%(asctime)s - %(name)s - %(filename)s - %(levelname)s line:%(lineno)s - %(user)s - %(status)s - %(message)s',
#         user="biasa", status="sad")

# logger = CustomLogger(
#     name = os.getenv("SERVICE_NAME"),
#     level = os.getenv("LEVEL"),
#     disable = os.getenv("LOG_DISABLE") == "true",
#     filterObject = generalFilter)

# adminLogger.info("aaaaaaaaa")
# """
