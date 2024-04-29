import re

class Router:
    def __init__(self):
        self.routes = []

    def add_route(self, method, path, func):
        path = re.compile(path)
        self.routes.append([method, path, func])

    def route_request(self, request):
        for route in self.routes:
            method = route[0]
            path = route[1]
            func = route[2]
            if method == request.method and path.match(request.path):
                return func(request)
        return b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n\r\n"