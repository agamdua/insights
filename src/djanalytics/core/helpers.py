import inspect

from pymongo import MongoClient

from django.conf import settings

from djanalytics.modulefs import modulefs

connection = MongoClient()

def import_view_modules():
    '''
    Step through the modules specified in INSTALLED_ANALYTICS_MODULES
    in settings.py, and import each of them. This must run on startup
    to make sure all of the event_handler decorators are called.
    '''
    top_level_modules = settings.INSTALLED_ANALYTICS_MODULES
    module_names = []
    for module in top_level_modules:
        mod = __import__(module)
        submodules = []
        try: 
            submodules = mod.modules_to_import # I'd like to deprecate this syntax
        except AttributeError: 
            pass
        for sub_module in submodules:
            submod_name = "{0}.{1}".format(module,sub_module)
            module_names.append(submod_name)
    modules = map(__import__, module_names)
    return modules

def namespace(f):
    return str(f.__module__).replace(".","_")

def get_database(f):
    ''' Given a function in a module, return the Mongo DB associated
    with that function. 
    '''
    return connection[namespace(f)]

def get_filesystem(f):
    ''' Given a function in a module, return the Pyfilesystem for that
    function. Right now, this is on disk, but it has to move to
    Mongo gridfs or S3 or similar (both of which are supported by 
    pyfs).
    '''
    return modulefs.get_filesystem(namespace(f))

def optional_parameter_call(function, optional_kwargs, passed_kwargs, arglist = None): 
    ''' Calls a function with parameters: 
    passed_kwargs are input parameters the function must take. 
    Format: Dictionary mapping keywords to arguments. 

    optional_kwargs are optional input parameters. 
    Format: Dictionary mapping keywords to functions which generate those parameters. 

    arglist is an optional list of arguments to pass to the function. 
    '''
    if not arglist: 
        arglist = inspect.getargspec(function).args
    
    args = {}
    for arg in arglist:
        # This order is important for security. We don't want users
        # being able to pass in 'fs' or 'db' and having that take
        # precedence. 
        if arg in optional_kwargs:
            args[arg] = optional_kwargs[arg](function)
        elif arg in passed_kwargs: 
            args[arg] = passed_kwargs[arg]
        else: 
            raise TypeError("Missing argument needed for handler ", arg)
    return function(**args)
