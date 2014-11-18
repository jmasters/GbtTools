import sys

def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')
 
    base36 = ''
    sign = ''
 
    if number < 0:
        sign = '-'
        number = -number
 
    if 0 <= number < len(alphabet):
        return sign + alphabet[number]
 
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
 
    return sign + base36
 
def base36decode(number):
    return int(number, 36)
 
if __name__ == '__main__':
    if len(sys.argv) == 2:
        if sys.argv[1].isdigit():
            print sys.argv[1],'==>',base36encode(int(sys.argv[1]))
        else:
            print sys.argv[1],'==>',base36decode(sys.argv[1])
    else:
        print 'Please supply one system id or AIPS extension to convert and try again.'
