

def mask_userid(userid, ndigits=2):
    symbols = list(str(userid))
    for i in range(0, len(symbols) - ndigits):
        symbols[i] = '#'
    return "".join(symbols)
