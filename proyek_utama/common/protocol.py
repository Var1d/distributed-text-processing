"""Protokol komunikasi: pesan JSON dengan prefix panjang 4 byte (TCP)."""
import json
import struct

MAX_MESSAGE_BYTES = 64 * 1024 * 1024

def send_msg(sock, obj):
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError(f"pesan terlalu besar: {len(data)} byte")
    sock.sendall(struct.pack(">I", len(data)) + data)

def _recv_exact(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("koneksi terputus")
        buf.extend(chunk)
    return bytes(buf)

def recv_msg(sock):
    (length,) = struct.unpack(">I", _recv_exact(sock, 4))
    if length > MAX_MESSAGE_BYTES:
        raise ValueError(f"pesan melebihi batas {MAX_MESSAGE_BYTES} byte")
    return json.loads(_recv_exact(sock, length).decode("utf-8"))
