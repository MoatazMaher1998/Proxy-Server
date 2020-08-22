# Don't forget to change this file's name before submission.
import socket
import sys
import os
import enum


class HttpRequestInfo(object):

    def __init__(self, client_info, method: str, requested_host: str,
                 requested_port: int,
                 requested_path: str,
                 headers: list):
        self.method = method
        self.client_address_info = client_info
        self.requested_host = requested_host
        self.requested_port = requested_port
        self.requested_path = requested_path
        self.headers = headers

    def to_http_string(self):
        Passer = self.method + " " + self.requested_path + " " + "HTTP/1.0" + "\r\n"
        while len(self.headers) != 0:
            Temp = self.headers.pop(0)
            Passer = Passer + Temp[0] + ":" + " " + Temp[1] + "\r\n"
        Passer = Passer + "\r\n"
        return Passer

    def to_byte_array(self, http_string):
        return bytes(http_string, "UTF-8")

    def display(self):
        print(f"Client:", self.client_address_info)
        print(f"Method:", self.method)
        print(f"Host:", self.requested_host)
        print(f"Port:", self.requested_port)
        stringified = [": ".join([k, v]) for (k, v) in self.headers]
        print("Headers:\n", "\n".join(stringified))


class HttpErrorResponse(object):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def to_http_string(self):
        return self.code + " " + self.message
        pass

    def to_byte_array(self, http_string):
        """
        Converts an HTTP string to a byte array.
        """
        return bytes(http_string, "UTF-8")

    def display(self):
        print(self.to_http_string())


class HttpRequestState(enum.Enum):

    INVALID_INPUT = 0
    NOT_SUPPORTED = 1
    GOOD = 2
    PLACEHOLDER = -1


def entry_point(proxy_port_number):
    Server_Socket = setup_sockets(proxy_port_number)
    while True:
        Connection, Address = Server_Socket.accept()
        Request = Connection.recv(1024)
        if Request.decode("UTF-8") in Cash.keys():
            print("Cashing ...")
            Response = Cash[Request.decode("UTF-8")]
        else:
            Response = http_request_pipeline(Address, Request)
        to_client(Response, Connection, Request)
    return None


def setup_sockets(proxy_port_number):
    print("Starting HTTP proxy on port:", proxy_port_number)
    Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Server_Socket.bind((get_arg(1, "127.0.0.1"), int(proxy_port_number)))
    Server_Socket.listen(15)
    return Server_Socket


def http_request_pipeline(source_addr, http_raw_data):
    Validity = check_http_request_validity(http_raw_data.decode("UTF-8"))
    if Validity is HttpRequestState.GOOD:
        Passer = parse_http_request(source_addr, http_raw_data.decode("UTF-8"))
        sanitize_http_request(Passer)
        STRING_TEMP = Passer.to_http_string()
        BYTE_ARRAY = Passer.to_byte_array(STRING_TEMP)
        Info = to_host(BYTE_ARRAY, Passer)
        return Info
    elif Validity is HttpRequestState.INVALID_INPUT:
        Error = HttpErrorResponse(400, "Bad Request")
        Error = Error.to_byte_array(Error.to_http_string())
        return Error
    elif Validity is HttpRequestState.NOT_SUPPORTED:
        Error = HttpErrorResponse(501, "Not Implemented")
        Error = Error.to_byte_array(Error.to_http_string())
        return Error
    else:
        return None


def parse_http_request(source_addr, http_raw_data) -> HttpRequestInfo:
    i = 0
    http_raw_data = http_raw_data.split("\r\n")
    Headers = http_raw_data[1:]
    MPV = http_raw_data[0].split(" ")
    try:
        Temp = MPV[1].split(":")[2].find("/")  # WITH URL http://WWW.GOOGLE.COM/:8080
        Port = MPV[1].split(":")[2][0:Temp]
    except:
        try:
            Port = Headers[0].split(":")[2].replace("/", "")  # WITH HEADER HOST: WWW.GOOGLE.COM:8080
        except:
            Port = 80

    Path = MPV[1]
    Headers_Not_Ready = http_raw_data[1:]
    Headers = []
    while Headers_Not_Ready[i] != "":
        Headers.append([Headers_Not_Ready[i].split(":")[0].lstrip(), Headers_Not_Ready[i].split(":")[1].lstrip()])
        i = i + 1
    try:
        Host = Headers_Not_Ready[0].split(":")[1].lstrip()
    except:
        Host = None
    Method = MPV[0]
    Ret = HttpRequestInfo(source_addr, Method, Host, Port, Path, Headers)
    return Ret


def check_http_request_validity(http_request_info: str) -> HttpRequestState:
    http_request_info = http_request_info.split("\r\n")
    MPV = http_request_info[0].split(" ")
    Headers = http_request_info[1:]
    if not MPV[2].__contains__("HTTP/"):
        return HttpRequestState.INVALID_INPUT
    if MPV[1].startswith("/"):
        if not Headers[0].__contains__("Host:"):
            return HttpRequestState.INVALID_INPUT
    elif not MPV[1].__contains__("http://"):
        return HttpRequestState.INVALID_INPUT
    if MPV[0] != "GET":
        if MPV[0] == "PUT" or MPV[0] == "HEAD" or MPV[0] == "POST":
            return HttpRequestState.NOT_SUPPORTED
        else:
            return HttpRequestState.INVALID_INPUT
    return HttpRequestState.GOOD


def sanitize_http_request(request_info: HttpRequestInfo) -> HttpRequestInfo:
    if request_info.requested_path.startswith("/"):
        return None
    elif "http" in request_info.requested_path:
        request_info.requested_path = request_info.requested_path.replace("http://", "")
        M = request_info.requested_path.find("/")
        Host = request_info.requested_path[0:M]
        Flag = Host.find(":")
        if Flag > 0:
            Host = Host[0:Flag]
        Path = request_info.requested_path[M:]
    request_info.requested_path = Path
    request_info.requested_host = Host


def to_host(request, info):
    print("Sending request now to host :")
    Server_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    Server_Socket.connect((info.requested_host, int(info.requested_port)))
    Server_Socket.send(request)
    Rec = Server_Socket.recv(1024)
    Temp = Rec
    while len(Rec) > 0:
        Rec = Server_Socket.recv(1024)
        Temp = Temp + Rec
    return Temp
    pass


def to_client(info, Connection, hashtable_request):
    print("Sending request now to client:")
    Cash[hashtable_request.decode("UTF-8")] = info
    Connection.send(info)
    Connection.close()
    pass


#######################################
# Leave the code below as is.
#######################################


def get_arg(param_index, default=None):
    """
        Gets a command line argument by index (note: index starts from 1)
        If the argument is not supplies, it tries to use a default value.

        If a default value isn't supplied, an error message is printed
        and terminates the program.
    """
    try:
        return sys.argv[param_index]
    except IndexError as e:
        if default:
            return default
        else:
            print(e)
            print(
                f"[FATAL] The comand-line argument #[{param_index}] is missing")
            exit(-1)  # Program execution failed.


def check_file_name():
    """
    Checks if this file has a valid name for *submission*

    leave this function and as and don't use it. it's just
    to notify you if you're submitting a file with a correct
    name.
    """
    script_name = os.path.basename(__file__)
    import re
    matches = re.findall(r"(\d{4}_){2}lab2\.py", script_name)
    if not matches:
        print(f"[WARN] File name is invalid [{script_name}]")


def main():
    """
    Please leave the code in this function as is.

    To add code that uses sockets, feel free to add functions
    above main and outside the classes.
    """
    print("\n\n")
    print("*" * 50)
    print(f"[LOG] Printing command line arguments [{', '.join(sys.argv)}]")
    check_file_name()
    print("*" * 50)

    # This argument is optional, defaults to 18888
    proxy_port_number = get_arg(2, 18888)
    entry_point(proxy_port_number)


if __name__ == "__main__":
    Cash = {}
    main()
