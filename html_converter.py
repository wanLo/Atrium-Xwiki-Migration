from ctypes import *
lib = cdll.LoadLibrary("html_converter/html2text.so")

class GoString(Structure):
    _fields_ = [("p", c_char_p), ("n", c_longlong)]

class FromString_ReturnType(Structure):
    _fields_ = [("r0", c_char_p), ("r1", c_char_p)]

lib.FromString_Py.argtypes = [GoString]
lib.FromString_Py.restype = FromString_ReturnType

def FromString(text):
    return (lib.FromString_Py(GoString(str.encode(text), len(text)))).r0

if __name__ == "__main__":
    print(FromString("<a href=\"asd.de\"> asd </a>"))

