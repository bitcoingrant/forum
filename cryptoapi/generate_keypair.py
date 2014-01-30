#!/usr/bin/env python
"""
Generate an ECDSA keypair and Bitcoin-compatible payment address.
Requires Brian Warner's excellent python-ecdsa library.

http://github.com/aristus/bitcoin-printer
"""
import ecdsa
from ecdsa.ecdsa import Public_key, Private_key, int_to_string
from ecdsa.ellipticcurve import CurveFp, Point
from ecdsa.util import string_to_number, number_to_string
from binascii import hexlify
import hashlib
import base64
from ecdsa.ecdsa import curve_secp256k1, generator_secp256k1
from ecdsa.curves import SECP256k1

#
# Credit for parts of this code goes to the Electrum bitcoin client https://github.com/spesmilo/electrum
#

# Bitcoin has an adorable encoding scheme that includes numbers and letters
# but excludes letters which look like numbers, eg "l" and "O"
# This appears to be from Electrum, please confirm by replacing this line
# with attribution

Hash = lambda x: hashlib.sha256(hashlib.sha256(x).digest()).digest()


def hash_160(public_key):
    try:
        md = hashlib.new('ripemd160')
        md.update(hashlib.sha256(public_key).digest())
        return md.digest()
    except:
        import ripemd
        md = ripemd.new(hashlib.sha256(public_key).digest())
        return md.digest()


def encode_point(pubkey, compressed=False):
    order = generator_secp256k1.order()
    p = pubkey.pubkey.point
    x_str = ecdsa.util.number_to_string(p.x(), order)
    y_str = ecdsa.util.number_to_string(p.y(), order)
    if compressed:
        return chr(2 + (p.y() & 1)) + x_str
    else:
        return chr(4) + pubkey.to_string()  # x_str + y_str


def rev_hex(s):
    return s.decode('hex')[::-1].encode('hex')


def int_to_hex(i, length=1):
    s = hex(i)[2:].rstrip('L')
    s = "0"*(2*length - len(s)) + s
    return rev_hex(s)


def var_int(i):
    # https://en.bitcoin.it/wiki/Protocol_specification#Variable_length_integer
    if i < 0xfd:
        return int_to_hex(i)
    elif i <= 0xffff:
        return "fd"+int_to_hex(i, 2)
    elif i <= 0xffffffff:
        return "fe"+int_to_hex(i, 4)
    else:
        return "ff"+int_to_hex(i, 8)


def msg_magic(message):
    varint = var_int(len(message))
    encoded_varint = "".join([chr(int(varint[i:i+2], 16))
                             for i in xrange(0, len(varint), 2)])

    # make message a bytestring
    return "\x18Bitcoin Signed Message:\n" + encoded_varint + message.encode('latin-1')


def b58encode(v):
    __b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    __b58base = len(__b58chars)
    long_value = 0L
    for (i, c) in enumerate(v[::-1]):
        long_value += (256**i) * ord(c)
    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result
    nPad = 0
    for c in v:
        if c == '\0':
            nPad += 1
        else:
            break
    return (__b58chars[0]*nPad) + result


def public_key_to_bc_address(public_key):
    h160 = hash_160(public_key)
    return hash_160_to_bc_address(h160)


def hash_160_to_bc_address(h160, addrtype=0):
    vh160 = chr(addrtype) + h160
    h = Hash(vh160)
    addr = vh160 + h[0:4]
    return b58encode(addr)


class EC_KEY(object):

    def __init__(self, secret):
        self.pubkey = ecdsa.ecdsa.Public_key(
            generator_secp256k1, generator_secp256k1 * secret)
        self.privkey = ecdsa.ecdsa.Private_key(self.pubkey, secret)
        self.secret = secret

    def sign_message(self, message, compressed, address):
        private_key = ecdsa.SigningKey.from_secret_exponent(
            self.secret, curve=SECP256k1)
        public_key = private_key.get_verifying_key()
        signature = private_key.sign_digest_deterministic(
            Hash(msg_magic(message)), hashfunc=hashlib.sha256, sigencode=ecdsa.util.sigencode_string)
        assert public_key.verify_digest(
            signature, Hash(msg_magic(message)), sigdecode=ecdsa.util.sigdecode_string)
        for i in range(4):
            sig = base64.b64encode(
                chr(27 + i + (4 if compressed else 0)) + signature)
            try:
                self.verify_message(address, sig, message)
                return sig
            except Exception as e:
                continue
        else:
            raise Exception("error: cannot sign message")

    @classmethod
    def verify_message(self, address, signature, message):
        """ See http://www.secg.org/download/aid-780/sec1-v2.pdf for the math """
        from ecdsa import numbertheory, ellipticcurve, util
        import msqr
        curve = curve_secp256k1
        G = generator_secp256k1
        order = G.order()
        # extract r,s from signature
        sig = base64.b64decode(signature)
        if len(sig) != 65:
            raise Exception("Wrong encoding")
        r, s = util.sigdecode_string(sig[1:], order)
        nV = ord(sig[0])
        if nV < 27 or nV >= 35:
            raise Exception("Bad encoding")
        if nV >= 31:
            compressed = True
            nV -= 4
        else:
            compressed = False

        recid = nV - 27
        # 1.1
        x = r + (recid/2) * order
        # 1.3
        alpha = (x * x * x + curve.a() * x + curve.b()) % curve.p()
        beta = msqr.modular_sqrt(alpha, curve.p())
        y = beta if (beta - recid) % 2 == 0 else curve.p() - beta
        # 1.4 the constructor checks that nR is at infinity
        R = ellipticcurve.Point(curve, x, y, order)
        # 1.5 compute e from message:
        h = Hash(msg_magic(message))
        e = string_to_number(h)
        minus_e = -e % order
        # 1.6 compute Q = r^-1 (sR - eG)
        inv_r = numbertheory.inverse_mod(r, order)
        Q = inv_r * (s * R + minus_e * G)
        public_key = ecdsa.VerifyingKey.from_public_point(
            Q, curve=SECP256k1)
        # check that Q is the public key
        public_key.verify_digest(
            sig[1:], h, sigdecode=ecdsa.util.sigdecode_string)
        # check that we get the original signing address
        addr = public_key_to_bc_address(encode_point(public_key, compressed))
        if address and address != addr:
            print addr, address
            raise Exception("Bad signature")
        # In case we don't know the signature
        return addr


def sign_message(secret, message):
    """ Sign a message given the numerical secret """
    key = EC_KEY(secret)
    return key.sign_message(message, False, generate_btc_address(secret)[3])


def generate_btc_address(secret):
    ripehash = hashlib.new('ripemd160')
    # secp256k1, not included in stock ecdsa
    _p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2FL
    _r = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141L
    _b = 0x0000000000000000000000000000000000000000000000000000000000000007L
    _a = 0x0000000000000000000000000000000000000000000000000000000000000000L
    _Gx = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798L
    _Gy = 0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8L
    curve_256 = CurveFp(_p, _a, _b)
    generator = Point(curve_256, _Gx, _Gy, _r)

    pubkey = Public_key(generator, generator * secret)
    step1 = '\x04' + int_to_string(pubkey.point.x()) + \
        int_to_string(pubkey.point.y())
    step2 = hashlib.sha256(step1).digest()
    ripehash.update(step2)
    step4 = '\x00' + ripehash.digest()
    step5 = hashlib.sha256(step4).digest()
    step6 = hashlib.sha256(step5).digest()
    chksum = step6[:4]
    addr = step4 + chksum
    addr_58 = b58encode(addr)
    return (
        hex(secret)[2:-1],
        hexlify(step1),
        hexlify(addr),
        addr_58
    )
