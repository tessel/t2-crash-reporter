from google.appengine.api import memcache
import os
import logging
import json
import jinja2

from model import from_milliseconds
from util import crash_uri, snippetize


# decorator for all requests
def common_request(callable_function):
    def wrapped_callable(*args, **kwargs):
        args_list = list(args)
        rrequest = RRequest(args_list[0])
        args_list[0] = rrequest
        try:
            return callable_function(*args_list, **kwargs)
        except Exception, e:
            logging.exception('Exception : %s' % unicode(e))
            rrequest.add_error('Exception : %s' % unicode(e))
            rrequest.add_to_json('error', unicode(e))
            rrequest.render('500.html')

    return wrapped_callable


def cache_it(key=None, time=86400):
    def decorator(callable_function):
        def wrapped_callable(*args, **kwargs):
            cached_value = memcache.get(key)
            if cached_value:
                return cached_value
            else:
                value = callable_function(*args, **kwargs)
                if value is not None:
                    memcache.set(key, value, time=time)
                return value

        return wrapped_callable

    return decorator


def readable_date(milliseconds):
    date_time = from_milliseconds(milliseconds)
    return date_time.strftime('%Y-%m-%d %H:%M:%S')


class RRequest(object):
    environment = None

    @classmethod
    def jinja2_environment(cls):
        # set the template search path to pages
        if not RRequest.environment:
            RRequest.environment = jinja2.Environment(
                loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'pages')))

            # add readable date filter to make it available for templates
            RRequest.environment.filters['readable_date'] = readable_date
            RRequest.environment.filters['crash_uri'] = crash_uri
            RRequest.environment.filters['snippetize'] = snippetize

        return RRequest.environment

    def __init__(self, request_handler):
        # handle to the current request context
        self.request_handler = request_handler

        # request context parameters
        self.params = {}

        # breadcrumbs
        self.breadcrumbs = []

        # error status for the request
        self.error = False

        # error messages
        self.errors = []

        # messages
        self.messages = []

        # json response
        self.json = {}

    def get_parameter(self, key, default_value=None, valid_iter=None):
        value = self.request_handler.request.get(key, default_value)
        if valid_iter:
            if value not in valid_iter:
                self.add_error('Invalid parameter for %s, \'%s\'.' % (key, value))
                value = None
        return value

    # checks if the specified keys in the query string are not in either request.GET | POST | FILES
    def empty_query_string(self, *args):
        if args:
            for key in args:
                value = self.get_parameter(key, None, None)
                if not value or len(value) <= 0:
                    return True
        return False

    def add_breadcrumb(self, name, href):
        self.breadcrumbs.append({'name': name, 'href': href})

    # adds new parameters to a request context
    def add_parameter(self, key, value):
        self.params[key] = value

    # adds a new message in the list of messages
    def add_message(self, message):
        self.messages.append(message)

    # adds an error to the list of errors
    def add_error(self, error):
        self.error = True
        self.errors.append(error)

    def add_to_json(self, key, value):
        self.json[key] = value

    def render(self, template_name):
        f = self.get_parameter('f', 'html', ['html', 'json', 'pjson'])
        p = self.get_parameter('pretty', 'false', ['true', 'false'])
        callback = self.get_parameter('callback')
        pretty = f == 'pjson' or p == 'true'
        if f == 'json' or f == 'pjson':
            '''Generate JSON response'''
            self.request_handler.response.headers['Content-Type'] = 'text/plain'
            self.request_handler.response.headers['Access-Control-Allow-Origin'] = '*'

            _json = self.json if self.json else {'errors': self.errors, 'messages': self.messages}
            jsonified_json = json.dumps(_json) if (pretty is False) else json.dumps(_json, indent=2)
            if callback is not None:
                jsonified_json = callback + '(' + jsonified_json + ');'
            self.request_handler.response.out.write(jsonified_json)
        else:
            '''Generate HTML response '''
            self.request_handler.response.out.write(
                RRequest.jinja2_environment().get_template(template_name).render({'rrequest': self}))
