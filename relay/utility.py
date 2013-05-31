def get_hex_dump(buffer_):
    dump = []
    i = 0
    while i < len(buffer_):
        dump.append('%02X' % (ord(buffer_[i])))
        
        i += 1

    return ' '.join(dump)
