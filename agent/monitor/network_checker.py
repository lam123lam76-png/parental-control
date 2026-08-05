import socket

def is_internet_available(host="8.8.8.8", port=53, timeout=3) -> bool:
    """
    Kiểm tra nhanh kết nối Internet qua socket TCP đến Google DNS.
    Trả về True nếu kết nối thành công, False nếu mất mạng.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.close()
        return True
    except socket.error:
        return False
