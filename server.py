from bson.json_util import dumps as bson
import json
import socketserver
import os
from util.request import Request
from util.auth import validate_password, extract_credentials
from util.multipart import parse_multipart
from util.websockets import WSFrame, compute_accept, parse_ws_frame, generate_ws_frame
import pymongo
import html
import bcrypt
import random
import hashlib


connections = []
users = {}

class MyTCPHandler(socketserver.BaseRequestHandler):

    def handle(self):
        global connections, users
        received_data = self.request.recv(2048)
        print(self.client_address)
        print("--- received data ---")
        print(received_data)
        print("--- end of data --- \n\n")
        original = len(received_data.split(b"\r\n\r\n")[0]) + 4
        if len(received_data) == 0:
            return
        temp = Request(received_data)
        if "Content-Length" in temp.headers:
            length = int(temp.headers["Content-Length"])
            if length >= 2048:
                for _ in range(0, length + original, min(2048, length + original - len(received_data))):
                    received_data += self.request.recv(min(2048, length + original - len(received_data)))
        request = Request(received_data)
        # TODO: Parse the HTTP request and use self.request.sendall(response) to send your response
        response = b"HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\nContent-Length: 36\r\n\r\nThe requested content does not exist"
        if request.path == "/":
            fileread = ""
            if "visits" in request.cookies:
                cookie = b"Set-Cookie: visits=" + str(int(request.cookies["visits"]) + 1).encode("utf-8") + b";Max-Age=7200\r\n"
                request.cookies["visits"] = str(int(request.cookies["visits"]) + 1)
            else:
                cookie = b"Set-Cookie: visits=1; Max-Age=7200"
                request.cookies["visits"] = 1
            with open("public/index.html", "r") as file1:
                fileread = file1.read()
                fileread = fileread.replace(r"{{visits}}", str(request.cookies["visits"]))
                random1 = random.randint(147483647, 2147483647)
                if "auth_token" in request.cookies:
                    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
                    db = myclient["cse312"]
                    user_collection = db["user"]
                    user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                    if user != None:
                        user_collection.update_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")}, {"$set": {"xsrf_token": random1}})
                        fileread = fileread.replace(r"{{xsrf_token}}", str(random1))
            body = fileread.encode("utf-8")
            size = len(body)
            response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(size).encode("utf-8") + b"\r\nContent-Type: text/html; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n" + cookie + b"\r\n\r\n" + body

        elif request.path == "/register":
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            user_collection = db["user"]
            auth = extract_credentials(request)
            username = auth[0]
            password = auth[1]
            if validate_password(password):
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
                if user_collection.find_one({"username": username}) == None:
                    user_collection.insert_one({"username": username, "password": hashed, "salt": salt, "auth_token": b"", "xsrf_token": b""})
            response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"

        elif request.path == "/login":
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            user_collection = db["user"]
            auth = extract_credentials(request)
            username = auth[0]
            password = auth[1]
            user = user_collection.find_one({"username": username})
            if user == None:
                response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
            else:
                salt = user["salt"]
                hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
                if hashed == user["password"]:
                    random1 = str(random.randint(147483647, 2147483647)).encode("utf-8")
                    auth_token = hashlib.sha256(random1).hexdigest().encode("utf-8")
                    user_collection.update_one({"username": username}, {"$set": {"auth_token": auth_token}})
                    response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\nSet-Cookie: auth_token=" + random1 + b"; Max-Age=7200; HttpOnly\r\n\r\n"
                else:
                    response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
        
        elif request.path == "/logout":
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            user_collection = db["user"]
            user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
            if user != None:
                user_collection.update_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")}, {"$set": {"auth_token": ""}})
            response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\nSet-Cookie: auth_token=; Max-Age=0; HttpOnly\r\n\r\n"
        
        elif request.path == "/upload-pic":
            mp = parse_multipart(request)
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            image_collection = db["images"]
            chat_collection = db["chat"]
            id_collection = db["id"]
            for part in mp.parts:
                if part.name == "upload" and part.headers["Content-Type"] == "image/jpeg":
                    count = image_collection.count_documents({})
                    if id_collection.count_documents({}) > 0:
                        id = list(id_collection.find({}))
                        id[0]["num"] += 1
                        id_collection.update_one({}, {"$set": {"num": id[0]["num"]}})
                    else:
                        id_collection.insert_one({"num": 0})
                        id = [{"num": 0}]
                    filename = "public/image/image" + str(count) + ".jpg"
                    with open(filename, "wb") as file:
                        file.write(part.content)
                    image_collection.insert_one({"image": filename})
                    if "auth_token" in request.cookies:
                        user_collection = db["user"]
                        user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                        if user != None:
                            chat_collection.insert_one({"message": f"<img src={filename} alt={filename}>", "username": user["username"], "id": id[0]["num"]})
                        else:
                            chat_collection.insert_one({"message": f"<img src={filename} alt={filename}>", "username": "Guest", "id": id[0]["num"]})
                    else:
                        chat_collection.insert_one({"message": f"<img src={filename} alt={filename}>", "username": "Guest", "id": id[0]["num"]})
                    response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                elif part.name == "upload" and part.headers["Content-Type"] == "video/mp4":
                    count = image_collection.count_documents({})
                    if id_collection.count_documents({}) > 0:
                        id = list(id_collection.find({}))
                        id[0]["num"] += 1
                        id_collection.update_one({}, {"$set": {"num": id[0]["num"]}})
                    else:
                        id_collection.insert_one({"num": 0})
                        id = [{"num": 0}]
                    filename = "public/image/video" + str(count) + ".mp4"
                    with open(filename, "wb") as file:
                        file.write(part.content)
                    image_collection.insert_one({"image": filename})
                    if "auth_token" in request.cookies:
                        user_collection = db["user"]
                        user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                        if user != None:
                            chat_collection.insert_one({"message": f"<video width=320 height=240 controls autoplay muted><source src={filename} type=video/mp4>Your browser does not support the video tag.</video>", "username": user["username"], "id": id[0]["num"]})
                        else:
                            chat_collection.insert_one({"message": f"<video width=320 height=240 controls autoplay muted><source src={filename} type=video/mp4>Your browser does not support the video tag.</video>", "username": "Guest", "id": id[0]["num"]})
                    else:
                        chat_collection.insert_one({"message": f"<video width=320 height=240 controls autoplay muted><source src={filename} type=video/mp4>Your browser does not support the video tag.</video>", "username": "Guest", "id": id[0]["num"]})
                    response = b"HTTP/1.1 302 Found\r\nLocation: /\r\nContent-Length: 0\r\nContent-Type: text/plain; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
        
        elif request.path == "/websocket":
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            chat_collection = db["chat"]
            id_collection = db["id"]
            user_collection = db["user"]
            if "auth_token" in request.cookies:
                user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                if user != None:
                    authenticated = user["username"]
                else:
                    authenticated = "Guest"
            else:
                authenticated = "Guest"
            accept = compute_accept(request.headers["Sec-WebSocket-Key"])
            response = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: " + str(accept).encode() + b"\r\n\r\n"
            self.request.sendall(response)
            if self not in connections:
                if authenticated != "Guest" and not any(authenticated in user for user in users.values()):
                    users[self] = authenticated
                connections.append(self)
            leftovers = b''
            while True:
                received_data = b''
                received_data += leftovers
                leftovers = b''
                received_data += self.request.recv(2048)
                multiple = []
                parsed = parse_ws_frame(received_data)
                buff = parsed.start

                if parsed.fin_bit == 0:
                    running = len(received_data)
                    data = received_data
                    arr = []
                    while parsed.fin_bit == 0:
                        total = parsed.payload_length + buff
                        for _ in range(0, total, min(2048, total - running)):
                            receive_data = self.request.recv(min(2048, total - running))
                            data += receive_data
                            running += len(receive_data)
                        payload = parse_ws_frame(data).payload
                        arr.append(payload)
                        newframe = self.request.recv(2048)
                        parsed = parse_ws_frame(newframe)   
                        data = newframe
                        buff = parsed.start
                        running = len(newframe)
                    total = parsed.payload_length + buff
                    for _ in range(0, total, min(2048, total - running)):
                        receive_data = self.request.recv(min(2048, total - running))
                        data += receive_data
                        running += len(receive_data)
                    payload = parse_ws_frame(data).payload
                    arr.append(payload)
                    payload = b''.join(arr)
                    parsed.opcode = 0x1

                elif len(received_data) > parsed.payload_length + buff:
                    for _ in range(0, len(received_data), parsed.payload_length + buff):
                        frame = received_data[parsed.payload_length + buff:]
                        received_data = received_data[:parsed.payload_length + buff]
                        parsed = parse_ws_frame(received_data)
                        multiple.append(parsed.payload)
                    received_data = received_data[parsed.payload_length + buff:]
                    leftovers = received_data[:parsed.payload_length + buff]

                elif parsed.payload_length > 2048:
                    for _ in range(0, parsed.payload_length + buff, min(2048, parsed.payload_length + buff - len(received_data))):
                        received_data += self.request.recv(min(2048, parsed.payload_length + buff - len(received_data)))
                    ws = parse_ws_frame(received_data)
                    payload = ws.payload

                else:
                    payload = parsed.payload

                print(connections)
                print(payload)

                if parsed.opcode == 0x8:
                    connections.remove(self)
                    if self in users:
                        del users[self]
                    break

                elif parsed.opcode == 0x1:
                    
                    if len(multiple) > 1:
                        for websocket in multiple:
                            load = json.loads(websocket)

                            if load["messageType"] == "chatMessage":
                                load["message"] = html.escape(load["message"])

                                if id_collection.count_documents({}) > 0:
                                    id = list(id_collection.find({}))
                                    id[0]["num"] += 1
                                    id_collection.update_one({}, {"$set": {"num": id[0]["num"]}})

                                else:
                                    id_collection.insert_one({"num": 0})
                                    id = [{"num": 0}]

                                dict = {"messageType": "chatMessage","message": load["message"],"username":authenticated, "id": id[0]["num"]}
                                chat_collection.insert_one(dict)
                                dict = bson(dict)
                                frame = generate_ws_frame(dict.encode("utf-8"))
                                for connection in connections:
                                    connection.request.sendall(frame)
                                    
                            if load["messageType"] == "userList":
                                userslist = list(users.values())
                                dict = {"messageType": "userList","users": userslist}
                                dict = bson(dict)
                                frame = generate_ws_frame(dict.encode("utf-8"))
                                print(frame)
                                self.request.sendall(frame)

                    else:
                        load = json.loads(payload)

                        if load["messageType"] == "chatMessage":
                            load["message"] = html.escape(load["message"])

                            if id_collection.count_documents({}) > 0:
                                id = list(id_collection.find({}))
                                id[0]["num"] += 1
                                id_collection.update_one({}, {"$set": {"num": id[0]["num"]}})

                            else:
                                id_collection.insert_one({"num": 0})
                                id = [{"num": 0}]

                            dict = {"messageType": "chatMessage","message": load["message"],"username":authenticated, "id": id[0]["num"]}
                            chat_collection.insert_one(dict)
                            dict = bson(dict)
                            frame = generate_ws_frame(dict.encode("utf-8"))
                            for connection in connections:
                                connection.request.sendall(frame)

                        if load["messageType"] == "userList":
                            userslist = list(users.values())
                            dict = {"messageType": "userList","users": userslist}
                            dict = bson(dict)
                            frame = generate_ws_frame(dict.encode("utf-8"))
                            self.request.sendall(frame)
        
        elif request.path[0:14] == "/chat-messages":
            myclient = pymongo.MongoClient("mongodb://localhost:27017/")
            db = myclient["cse312"]
            chat_collection = db["chat"]    
            id_collection = db["id"]

            if request.method == "POST":
                dictionary = json.loads(request.body)
                dictionary["message"] = html.escape(dictionary["message"])
                token = dictionary["xsrf_token"]
                if id_collection.count_documents({}) > 0:
                    id = list(id_collection.find({}))
                    id[0]["num"] += 1
                    id_collection.update_one({}, {"$set": {"num": id[0]["num"]}})
                else:
                    id_collection.insert_one({"num": 0})
                    id = [{"num": 0}]
                if "auth_token" in request.cookies:
                    user_collection = db["user"]
                    user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                    if user != None and int(user["xsrf_token"]) == int(token):
                        dict = {"message": dictionary["message"],"username":user["username"], "id": id[0]["num"]}
                        response = b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                        chat_collection.insert_one(dict)
                        dict = bson(dict)
                    elif user == None:
                        dict = {"message": dictionary["message"],"username":"Guest", "id": id[0]["num"]}
                        response = b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                        chat_collection.insert_one(dict)
                        dict = bson(dict)
                    else:
                        response = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                else:
                    dict = {"message": dictionary["message"],"username":"Guest", "id": id[0]["num"]}
                    response = b"HTTP/1.1 201 Created\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                    chat_collection.insert_one(dict)
                    dict = bson(dict)

            elif request.method == "GET":
                if request.path == "/chat-messages":
                    chat = list(chat_collection.find({}))
                    chat = bson(chat)
                    response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(chat)).encode("utf-8") + b"\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n" + chat.encode("utf-8")
                else:
                    chat = chat_collection.find_one({"id": int(request.path[15:])})
                    if chat == None:
                        response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                    else:
                        chat = bson(list(chat))
                        response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(chat)).encode("utf-8") + b"\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n" + chat.encode("utf-8")
            
            elif request.method == "DELETE":
                chat = chat_collection.find_one({"id": int(request.path[15:])})
                if chat == None:
                    response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                else:
                    if "auth_token" in request.cookies:
                        user_collection = db["user"]
                        user = user_collection.find_one({"auth_token": hashlib.sha256(bytes(request.cookies["auth_token"], "utf-8")).hexdigest().encode("utf-8")})
                        if user != None and user["username"] == chat["username"]:
                            chat_collection.delete_one({"id": int(request.path[15:])})
                            response = b"HTTP/1.1 200 OK\r\nContent-Length: 31\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\nRegistered user deleted message"
                        elif user["username"] != chat["username"]:
                            response = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                    else:
                        if chat["username"] == "Guest":
                            chat_collection.delete_one({"id": int(request.path[15:])})
                            response = b"HTTP/1.1 200 OK\r\nContent-Length: 30\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\nGuest user deleted message"
                        else:
                            response = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                    
            elif request.method == "PUT":
                chat = chat_collection.find_one({"id": int(request.path[15:])})
                if chat == None:
                    response = b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                dictionary = json.loads(request.body)
                dictionary["message"] = html.escape(dictionary["message"])
                dict = {"message": dictionary["message"],"username":dictionary["username"], "id": int(request.path[15:])}
                chat_collection.update_one({"id": int(request.path[15:])}, {"$set": dict})
                dict = bson(dict)
                response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(len(dict)).encode("utf-8") + b"\r\nContent-Type: application/json; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n" + dict.encode("utf-8")

        elif os.path.exists(os.getcwd() + request.path):
            path = os.getcwd() + request.path
            if request.path[0:13] == "/public/image":
                removeslash = request.path[13:].replace("/", "")
                path = os.getcwd() + "/public/image/" + removeslash 
                size = os.stat(path).st_size
                response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(size).encode("utf-8") + b"\r\nContent-Type: image/jpeg; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                with open(path, "rb") as file:
                    response += file.read()

            elif request.path.endswith(".js"):
                size = os.stat(path).st_size
                response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(size).encode("utf-8") + b"\r\nContent-Type: text/javascript; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                with open(path, "rb") as file:
                    response += file.read()

            elif request.path.endswith(".css"):
                size = os.stat(path).st_size
                response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(size).encode("utf-8") + b"\r\nContent-Type: text/css; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                with open(path, "rb") as file:
                    response += file.read()

            elif request.path.endswith(".ico"):
                size = os.stat(path).st_size
                response = b"HTTP/1.1 200 OK\r\nContent-Length: " + str(size).encode("utf-8") + b"\r\nContent-Type: image/vnd.microsoft.icon; charset=utf-8\r\nX-Content-Type-Options: nosniff\r\n\r\n"
                with open(path, "rb") as file:
                    response += file.read()
        self.request.sendall(response)


def main():
    host = "0.0.0.0"
    port = 8080

    socketserver.TCPServer.allow_reuse_address = True

    server = socketserver.ThreadingTCPServer((host, port), MyTCPHandler)

    print("Listening on port " + str(port))

    server.serve_forever()  


if __name__ == "__main__":
    main()
