"""
Micropython HTTP Asynchronous Service like Flask.
"""

import ure
import ujson
import ulogging

log = ulogging.getLogger(__name__)

statuses = {
    # from https://stackoverflow.com/questions/36528175, https://cdn.unreal-designs.co.uk/cont/statusMsg/
    "1": ("Information", ""),
    100: ("Continue", "The server has received the request headers, and the client should proceed to send the request body"),
    101: ("Switching Protocols", "The requester has asked the server to switch protocols"),
    103: ("Checkpoint", "Used in the resumable requests proposal to resume aborted PUT or POST requests"),
    "2": ("Successful", ""),
    200: ("OK", "The request is OK (this is the standard response for successful HTTP requests)"),
    201: ("Created", "The request has been fulfilled, and a new resource is created"),
    202: ("Accepted", "The request has been accepted for processing, but the processing has not been completed"),
    203: ("Non-Authoritative Information", "The request has been successfully processed, but is returning information that may be from another source"),
    204: ("No Content", "The request has been successfully processed, but is not returning any content"),
    205: ("Reset Content", "The request has been successfully processed, but is not returning any content, and requires that the requester reset the document view"),
    206: ("Partial Content", "The server is delivering only part of the resource due to a range header sent by the client"),
    "3": ("Redirection", ""),
    300: ("Multiple Choices", "A link list. The user can select a link and go to that location. Maximum five addresses"),
    301: ("Moved Permanently", "The requested page has moved to a new URL"),
    302: ("Found", "The requested page has moved temporarily to a new URL"),
    303: ("See Other", "The requested page can be found under a different URL"),
    304: ("Not Modified", "Indicates the requested page has not been modified since last requested"),
    306: ("Switch Proxy", "-- No longer used --"),
    307: ("Temporary Redirect", "The requested page has moved temporarily to a new URL"),
    308: ("Resume Incomplete", "Used in the resumable requests proposal to resume aborted PUT or POST requests"),
    "4": ("Client Error", ""),
    400: ("Bad Request", "The request cannot be fulfilled due to bad syntax"),
    401: ("Unauthorized", "The request was a legal request, but the server is refusing to respond to it. For use when authentication is possible but has failed or not yet been provided"),
    402: ("Payment Required", "-- Reserved for future use --"),
    403: ("Forbidden", "The request was a legal request, but the server is refusing to respond to it"),
    404: ("Not Found", "The requested page could not be found but may be available again in the future"),
    405: ("Method Not Allowed", "A request was made of a page using a request method not supported by that page"),
    406: ("Not Acceptable", "The server can only generate a response that is not accepted by the client"),
    407: ("Proxy Authentication Required", "The client must first authenticate itself with the proxy"),
    408: ("Request Timeout", "The server timed out waiting for the request"),
    409: ("Conflict", "The request could not be completed because of a conflict in the request"),
    410: ("Gone", "The requested page is no longer available"),
    411: ("Length Required", "The \"Content-Length\" is not defined. The server will not accept the request without it"),
    412: ("Precondition Failed", "The precondition given in the request evaluated to false by the server"),
    413: ("Request Entity Too Large", "The server will not accept the request, because the request entity is too large"),
    414: ("Request-URI Too Long", "The server will not accept the request, because the URL is too long. Occurs when you convert a POST request to a GET request with a long query information"),
    415: ("Unsupported Media Type", "The server will not accept the request, because the media type is not supported"),
    416: ("Requested Range Not Satisfiable", "The client has asked for a portion of the file, but the server cannot supply that portion"),
    417: ("Expectation Failed", "The server cannot meet the requirements of the Expect request-header field"),
    418: ("I'm a teapot", "Any attempt to brew coffee with a teapot should result in the error code \"418 I'm a teapot\". The resulting entity body MAY be short and stout"),
    421: ("Misdirected Request", "The request was directed at a server that is not able to produce a response (for example because a connection reuse)"),
    422: ("Unprocessable Entity", "The request was well-formed but was unable to be followed due to semantic errors"),
    423: ("Locked", "The resource that is being accessed is locked"),
    424: ("Failed Dependency", "The request failed due to failure of a previous request (e.g., a PROPPATCH)"),
    426: ("Upgrade Required", "The client should switch to a different protocol such as TLS\/1.0, given in the Upgrade header field"),
    428: ("Precondition Required", "The origin server requires the request to be conditional"),
    429: ("Too Many Requests", "The user has sent too many requests in a given amount of time. Intended for use with rate limiting schemes"),
    431: ("Request Header Fields Too Large", "The server is unwilling to process the request because either an individual header field, or all the header fields collectively, are too large"),
    451: ("Unavailable For Legal Reasons", "A server operator has received a legal demand to deny access to a resource or to a set of resources that includes the requested resource"),
    "5": ("Server Error", ""),
    500: ("Internal Server Error", "An error has occured in a server side script, a no more specific message is suitable"),
    501: ("Not Implemented", "The server either does not recognize the request method, or it lacks the ability to fulfill the request"),
    502: ("Bad Gateway", "The server was acting as a gateway or proxy and received an invalid response from the upstream server"),
    503: ("Service Unavailable", "The server is currently unavailable (overloaded or down)"),
    504: ("Gateway Timeout", "The server was acting as a gateway or proxy and did not receive a timely response from the upstream server"),
    505: ("HTTP Version Not Supported", "The server does not support the HTTP protocol version used in the request"),
    511: ("Network Authentication Required", "The client needs to authenticate to gain network access")}

def getstatus(code):
    """
    Return a tuple of (name, description) for the given status `code`.
    Failsafe to a default unknown name and description if `code` is non existant.
    """
    try:
        name, description = statuses.get(int(code), statuses[str(code)[0]])
    except:
        name, description = 'Unknown', 'The meaning of this HTTP status is unknown.'
    return name, description

class HTTPException(Exception):
    """
    Base exception that is translated to HTTP Response in `Response.handle`.
    """
    def __init__(self, *args, status=500, **kwargs):
        super().__init__(*args, **kwargs)
        self.status = status

class Socket(object):
    """
    Abstract Socket implementation for serving.
    """
    def __init__(self, app):
        self.app = app

    def run(self, host, port):
        """
        Connect and listen to network socket and reply to requests.
        """
        raise NotImplementedError('Implement socket handling')

class Asyncio(Socket):
    """
    Asyncio Socket implementation.
    """
    def run(self, host, port):
        import uasyncio
        try:
            loop = uasyncio.get_event_loop()
            loop.create_task(uasyncio.start_server(self.serve, host, port))
            loop.run_forever()
        finally:
            loop.close()

    def serve(self, reader, writer):
        request = yield from reader.read()
        if request:
            response = self.app.handle(request)
            bytes = str(response).encode()
            yield from writer.awrite(bytes)
        yield from writer.aclose()

class Timer(Socket):
    """
    Timer Socket implementation.
    """
    # FIXME: Use socket 'with' statements: https://realpython.com/python-sockets/
    def run(self, host, port):
        import usocket
        import machine
        self.socket = usocket.socket()
        addr = (host, port)  # FIXME: should use getaddrinfo ?
        self.socket.bind(addr)
        self.socket.settimeout(0.1)
        self.socket.listen(0)
        self.timer = machine.Timer(-1)
        self.timer.init(period=1000, callback=lambda t: self.serve())

    def serve(self):
        try:
            conn, host = self.socket.accept()
            request = conn.recv(8192)  # FIXME: hitting EOF creates a lag
        except OSError:
            return  # expected behavior when socket.accept reaches timeout
                    # FIXME: catch more specific exception OSError: [Errno 110] ETIMEDOUT ?
        try:
            response = str(self.app.handle(request)).encode()
            conn.sendall(response)
        # except Exception as e:
        #     conn.send(('Error: %s: %s'%(e.__class__, __name__, str(e))).encode())
        finally:
            conn.close()

class Request(object):
    """
    Represent an HTTP Request.
    """
    def __init__(self, bites):
        bang, *content = bites.decode().splitlines()
        self.method, self.path, self.protocol = bang.split()
        self.body = ''.join(content[1+content.index(''):])
        self.headers = {}
        for header in content[:content.index('')]:
            k, v = header.split(':', 1)
            self.headers[k.strip()] = v.strip()

    def json(self, failsafe=True):
        try:
            return ujson.loads(self.body)
        except Exception as e:
            if failsafe:
                return None
            else:
                raise HTTPException('Invalid JSON (%s)'%e, status=400)

    def __str__(self):
        return '%s %s' % (self.method, self.path)

class Response(object):
    """
    Represent an HTTP Response.
    """
    status = None
    headers = {
        'server': 'mhask/0.0.0',
        'content-type': 'text/plain'}
    body = b''

    def __init__(self, body=None, status=200, headers={}):
        self.status = int(status)
        if body is not None:
            self.body = str(body)
        else:
            self.body = ': '.join(filter(bool, ((str(status),) + getstatus(status))))
        self.headers = dict(dict({}, **Response.headers), **headers)

    def __str__(self):
        self.headers['content-length'] = len(self.body)
        s = 'HTTP/1.0 %s %s\r\n' % (self.status, getstatus(self.status)[0])
        s += ''.join(['%s: %s\r\n' % (k, v) for k, v in self.headers.items()])
        s += '\r\n%s\r\n' % self.body
        return s

class App(object):
    """
    App.
    """
    name = None
    endpoints = {}
    request = None  # FIXME: current request (not concurrent-friendly)
    debug = False

    def route(self, route, methods=['GET']):
        """
        Decorator to bind a function to a route.
        """
        def wrap(f):
            log.debug("Adding route %s for %s to %s" % (route, methods, f))
            self.endpoints[route, tuple(methods)] = f
            return f
        return wrap

    def resolve(self, request):
        """
        Return a tuple of (route, methods, callback, arguments) matching the given request.
        """
        endpoints = sorted(
            item for item in self.endpoints.items(),
            key=lambda l: len(l[0][0]),
            reverse=True)

        for endpoint, callback in endpoints:
            route, methods = endpoint
            if request.method in methods:
                pattern = '/'.join(c.replace(':%s'%c[1:], '[^/].*') for c in route.split('/'))
                pattern = '^%s$' % pattern
                log.debug('Matching %s %s against %s %s (regex: %s)' % (request.method, request.path, methods, route, pattern))
                if ure.match(pattern, request.path):
                    log.debug('Matched %s %s with %s %s', request.method, request.path, methods, route)
                    arguments = {}
                    for i, component in enumerate(route.split('/')):
                        if component.startswith(':'):
                            value = request.path.split('/')[i]
                            if len(value):
                                argument = component.lstrip(':')
                                arguments[argument] = value
                    return route, methods, callback, arguments
        raise HTTPException('No route found for request %s' % request, status=404)

    def handle(self, bytes):
        """
        Handle the given `bytes` and return a `Response`.
        """
        log.debug('Handling request: %s' % bytes)
        self.request = Request(bytes)
        try:
            route, methods, callback, arguments = self.resolve(self.request)
            result = callback(**arguments)
        except HTTPException as e:
            result = Response(str(e), e.status)
        except Exception as e:
            result = Response('%s: %s' % (e.__class__.__name__, str(e)), 500)
            if self.debug:
                raise
        finally:
            try: route, methods, callback, arguments
            except: route = methods = callback = arguments = None

        response = result if isinstance(result, Response) else Response(result)
        log.debug('Computed response: %s', repr(str(response)))
        log.info('%s %s -> %s %s %s -> %s' % (self.request.method, self.request.path, route, arguments, callback, response.status))
        return response

    def run(self, host='0.0.0.0', port=80, socket=Asyncio):
        """
        Run the `App` instance on the given `host` and `port` using the given `socket`.
        """
        log.info('Running HTTP Server %s on %s:%s (debug: %s)' % (socket, host, port, self.debug))
        if self.debug:
            log.setLevel(ulogging.DEBUG)
        socket(self).run(host, port)
