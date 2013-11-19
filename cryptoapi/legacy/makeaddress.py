'''
99% of this code was written by Jonathan
Jul 18th 2013
He's awesome
'''
import crypto
import hashlib

ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

def encodeBase58(num, alphabet=ALPHABET):
    """Encode a number in Base X

    `num`: The number to encode
    `alphabet`: The alphabet to use for encoding
    """
    if (num == 0):
        return alphabet[0]
    arr = []
    base = len(alphabet)
    while num:
        rem = num % base
        #print 'num is:', num
        num = num // base
        arr.append(alphabet[rem])
    arr.reverse()
    return ''.join(arr)

def makeaddress(priv_key):
    print " - Make Bitcoin Address - "
    publicKey = crypto.privToPub(priv_key).decode('hex')
    print publicKey.encode('hex')
    firstHash = hashlib.sha256(publicKey).digest()
    ripe = hashlib.new('ripemd160')
    ripe.update(firstHash)
    secondHash = ripe.digest()
    print "Step 3: " + secondHash.encode('hex')
    secondHash = '\x00'+ secondHash# Add version byte
    print "Step 4: " + secondHash.encode('hex')
    checksum = hashlib.sha256(hashlib.sha256(secondHash).digest()).digest()[:4]
    print "Checksum: " + checksum.encode('hex')
    binaryBitcoinAddress = secondHash + checksum
    numberOfZeroBytesOnBinaryBitcoinAddress = 0
    # For every \x00 on the front of binaryBitcoinAddress, we need to take it off and later prepend a "1"
    while binaryBitcoinAddress[0] == '\x00':
        numberOfZeroBytesOnBinaryBitcoinAddress += 1
        binaryBitcoinAddress = binaryBitcoinAddress[1:]
    intBitcoinAddress = int(binaryBitcoinAddress.encode('hex'),16)
    base58encoded = encodeBase58(intBitcoinAddress)
    return "1" * numberOfZeroBytesOnBinaryBitcoinAddress + base58encoded
    
    
#potential bug, passed private key cannot start with lowercase s or lowercase n. Probably more characters than that though.
#makeaddress('bitcoin')
