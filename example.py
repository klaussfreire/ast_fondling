
def validate_range(x):
    return 0 <= x < 10000

def format_date(y, mo, d, h, mi, s):
    return str(y) + "-" + str(mo) + "-" + str(d) + "T" + str(h) + ":" + str(mi) + ":" + str(s)

def format_bytes(x):
    scale = 0
    while x > 1000:
        x /= 1000.0
        scale += 1

    SCALES = [ "B", "kB", "MB", "GB", "TB", "PB" ]

    x = int(x*100)
    return str(x//100) + "." + str(x%100) + " " + SCALES[scale]

def filter(f, l):
    return [ x for x in l if f(x) ]

def filter_null(l):
    return filter(lambda x : x is None, l)

print validate_range(-30)
print validate_range(30)
print validate_range(1 << 30)
print format_date(2017, 10, 1, 13, 30, 10)
print format_bytes((1.3 * (1 << 30)) if (1 << 30) < (1 << 31) else 1.2 * (1 << 20))
print "pares", filter(lambda x : (x % 2) == 0, [1, 2, 3, 4, 5, 10, 11])
print "impares", filter(lambda x : (x % 2) != 0, [1, 2, 3, 4, 5, 10, 11])
