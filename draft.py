def split_tokens(tokens, delimiter):
    def gen():
        while tokens:
            tokens[:], token = tokens[1:], tokens[0]
            if token == delimiter: return
            yield token
    while tokens:
        yield gen()

tokens = [1,0,1,3,0,4]
for g in split_tokens(tokens, 0):
    for n in g:
        print(n, end=' ')
    print()