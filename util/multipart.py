#import request
class Part:
    def __init__(self):
        self.headers = {}
        self.name = None
        self.content = None

class Multipart:
    def __init__(self):
        self.boundary = None
        self.parts = []


def parse_multipart(request) -> Multipart:
    mp = Multipart()
    mp.boundary = request.headers['Content-Type'].split('boundary=')[1]
    parts = request.body.split(b'--' + bytes(mp.boundary, 'utf-8'))
    parts = parts[1:-1]
    for part in parts:
        p = Part()
        headers, p.content = part.split(b'\r\n\r\n', 1)
        headers = headers.split(b'\r\n')
        headers = headers[1:]
        if p.content[-2:] == b'\r\n':
            p.content = p.content[:-2]
        for header in headers:
            key, value = header.split(b': ')
            p.headers[key.decode('utf-8')] = value.decode('utf-8')
            if key == b'Content-Disposition':
                p.name = value.decode('utf-8').split('; ')[1].split('=')[1].strip('"')
        mp.parts.append(p)
    return mp

# def test1():
#     req = request.Request(b'POST /form-path HTTP/1.1\r\nContent-Length: 10000\r\nContent-Type: multipart/form-data; boundary=----thisboundary\r\n\r\n------thisboundary\r\nContent-Disposition: form-data; name="commenter"\r\n\r\nJesse\r\n------thisboundary\r\nContent-Disposition: form-data; name="upload"; filename="cat.png"\r\nContent-Type: image/png\r\n\r\n<bytes_of_file>\r\n------thisboundary--')
#     mp = parse_multipart(req)
#     assert mp.boundary == '----thisboundary'
#     assert len(mp.parts) == 2
#     assert mp.parts[0].name == 'commenter'
#     assert mp.parts[0].content == b'Jesse'
#     assert mp.parts[1].name == 'upload'
#     assert mp.parts[1].headers['Content-Type'] == 'image/png'
#     assert mp.parts[1].content == b'<bytes_of_file>'

#     print('test1 passed')

# if __name__ == '__main__':
#     test1()