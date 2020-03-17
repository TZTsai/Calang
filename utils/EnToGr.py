import re

def en_to_gr(ch):
    en_start = ord('A')
    gr_start = ord('\u0391')
    return chr(ord(ch) + gr_start - en_start)

def escape_to_greek(s):
    return re.sub(r'\\([a-zA-Z])', lambda m: en_to_gr(m[1]), s)


if __name__ == "__main__":
    print(en_to_gr('a'))
    print(en_to_gr('b'))
    print(en_to_gr('S'))
    print(escape_to_greek('\\a \\bXy\\c1 \\D3'))