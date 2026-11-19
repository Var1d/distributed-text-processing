import json
import struct
import socket
from typing import Any

# Maksimum ukuran satu pesan: 64 MB
MAX_MESSAGE_SIZE = 64 * 1024 * 1024


def encode_message(data: dict[str, Any]) -> bytes:
    """
    Mengubah dictionary menjadi pesan JSON
    dengan 4-byte length prefix.
    """

    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")

    if len(payload) > MAX_MESSAGE_SIZE:
        raise ValueError("Ukuran pesan melebihi batas maksimum.")

    header = struct.pack("!I", len(payload))

    return header + payload


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """
    Membaca sejumlah byte sampai lengkap.
    """

    chunks = []
    remaining = size

    while remaining > 0:
        chunk = sock.recv(remaining)

        if not chunk:
            raise ConnectionError("Koneksi terputus sebelum pesan lengkap diterima.")

        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def send_message(sock: socket.socket, data: dict[str, Any]) -> None:
    """
    Mengirim satu pesan lengkap melalui TCP.
    """

    message = encode_message(data)
    sock.sendall(message)


def recv_message(sock: socket.socket) -> dict[str, Any] | None:
    """
    Menerima satu pesan lengkap melalui TCP.

    Mengembalikan None jika koneksi ditutup
    secara normal sebelum header pesan diterima.
    """

    header = sock.recv(4)

    if not header:
        return None

    if len(header) < 4:
        header += recv_exact(sock, 4 - len(header))

    message_length = struct.unpack("!I", header)[0]

    if message_length == 0 or message_length > MAX_MESSAGE_SIZE:
        raise ValueError("Ukuran pesan tidak valid.")

    payload = recv_exact(sock, message_length)

    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Format pesan JSON tidak valid.") from exc

    if not isinstance(data, dict):
        raise ValueError("Pesan harus berupa JSON object.")

    return data
