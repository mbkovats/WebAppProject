import hashlib
import base64
class WSFrame:
    def __init__(self):
        self.fin_bit = 0
        self.opcode = 0
        self.payload_length = 0
        self.payload = b""
        self.start = 0
def compute_accept(key):
    key += "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    key = hashlib.sha1(key.encode())
    return base64.b64encode(key.digest()).decode()
def parse_ws_frame(frame):
    ws = WSFrame()
    ws.fin_bit = frame[0] >> 7
    ws.opcode = frame[0] & 0x0F
    ws.payload_length = frame[1] & 0x7F
    mask = frame[1] >> 7
    start = 2
    if ws.payload_length == 126:
        ws.payload_length = int.from_bytes(frame[2:4], byteorder="big")
        start = 4
    elif ws.payload_length == 127:
        ws.payload_length = int.from_bytes(frame[2:10], byteorder="big")
        start = 10
    if mask:
        mask_key = frame[start:start+4]
        start += 4
    ws.payload = frame[start:]
    ws.start = start
    if mask:
        payload_bytes = []
        for i in range(len(ws.payload)):
            masked_byte = ws.payload[i] ^ mask_key[i & 3]
            payload_bytes.append(masked_byte)
        ws.payload = bytes(payload_bytes)
    return ws
def generate_ws_frame(payload: bytes):
    fin_bit = 0x1
    opcode = 0x0001
    payload_length = len(payload)
    if payload_length < 126:
        frame = bytearray([fin_bit << 7 | opcode])
        frame.append(payload_length)
    elif payload_length < 65536:
        frame = bytearray([fin_bit << 7 | opcode])
        frame.append(126)
        frame += payload_length.to_bytes(2, byteorder="big")
    else:
        frame = bytearray([fin_bit << 7 | opcode])
        frame.append(127)
        frame += payload_length.to_bytes(8, byteorder="big")
    frame += payload
    return frame
