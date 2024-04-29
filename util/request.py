class Request:

    def __init__(self, request: bytes):
        # TODO: parse the bytes of the request and populate the following instance variables

        self.body = b""
        self.method = ""
        self.path = ""
        self.http_version = ""
        self.headers = {}
        self.cookies = {}
        req = request.split(b'\r\n')
        body = request.split(b'\r\n\r\n', 1)
        self.method = str(req[0].split(b' ')[0], "utf-8")
        self.path = str(req[0].split(b' ')[1], "utf-8")
        self.http_version = str(req[0].split(b' ')[2], "utf-8") 
        for i in range(1, len(req)):
            if req[i] == b'':
                break
            header = req[i].split(b': ')
            self.headers[str(header[0], "utf-8")] = str(header[1], "utf-8")
        if 'Cookie' in self.headers:
            cookies = self.headers['Cookie'].split('; ')
            for cookie in cookies:
                cookie = cookie.split('=')
                self.cookies[cookie[0]] = cookie[1]
        if self.method == 'POST':
            self.body = body[1]

def test1():
    request = Request(b'GET / HTTP/1.1\r\nHost: localhost:8080\r\nConnection: keep-alive\r\nCookie: hello=world\r\n')
    assert request.method == "GET"
    assert "Host" in request.headers
    assert request.headers["Host"] == "localhost:8080"  # note: The leading space in the header value must be removed
    assert request.body == b"" 
    assert request.cookies["hello"] == "world"
    # There is no body for this request.
    # When parsing POST requests, the body must be in bytes, not str

    # This is the start of a simple way (ie. no external libraries) to test your code.
    # It's recommended that you complete this test and add others, including at least one
    # test using a POST request. Also, ensure that the types of all values are correct


if __name__ == '__main__':
    test1()
