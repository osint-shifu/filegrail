"""Checksums that let a value vouch for itself.

Every detector in `identify` has to decide whether a run of characters is an
identifier or a coincidence, and most of them decide it from shape and context:
a known TLD, a hemisphere letter, the name of the field. The values here carry
the decision inside them. A wallet address, a bank account and a tax number
each end in digits computed from the rest, so one changed character fails, and
a match can be believed without a region hint or a surrounding label.

That certainty has a floor. A check digit in base ten passes one random number
in ten; the Polish numbers, taken modulo eleven, pass about one in eleven. The
Bitcoin checksums are thirty bits and never pass by accident. The callers know
which is which: the tax numbers are only taken beside the label that names
them, and the addresses are taken wherever they stand.

Everything here is the standard library. The Base58Check digest is two rounds
of SHA-256; the Bech32 polynomial is thirty lines of arithmetic; mod-97 is a
long division.
"""

from __future__ import annotations

import base64
import hashlib

_BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

_BECH32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_BECH32_CONSTANT = 1
_BECH32M_CONSTANT = 0x2BC830A3
_BECH32_GENERATOR = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)

#: The one human-readable part a mainnet address can have.
_MAINNET = "bc"

#: The length an IBAN has in each country that has adopted the standard, from
#: the ISO 13616 registry. A country that is not here has no IBAN, and a
#: number of the wrong length for its country cannot be one however its
#: check digits come out.
_IBAN_LENGTHS = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16,
    "BG": 22, "BH": 22, "BI": 27, "BR": 29, "BY": 28, "CH": 21, "CR": 22,
    "CY": 28, "CZ": 24, "DE": 22, "DJ": 27, "DK": 18, "DO": 28, "EE": 20,
    "EG": 29, "ES": 24, "FI": 18, "FK": 18, "FO": 18, "FR": 27, "GB": 22,
    "GE": 22, "GI": 23, "GL": 18, "GR": 27, "GT": 28, "HR": 21, "HU": 28,
    "IE": 22, "IL": 23, "IQ": 23, "IS": 26, "IT": 27, "JO": 30, "KW": 30,
    "KZ": 20, "LB": 28, "LC": 32, "LI": 21, "LT": 20, "LU": 20, "LV": 21,
    "LY": 25, "MC": 27, "MD": 24, "ME": 22, "MK": 19, "MN": 20, "MR": 27,
    "MT": 31, "MU": 30, "NI": 28, "NL": 18, "NO": 15, "OM": 23, "PK": 24,
    "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22, "RU": 33,
    "SA": 24, "SC": 31, "SD": 18, "SE": 24, "SI": 19, "SK": 24, "SM": 27,
    "SO": 23, "ST": 25, "SV": 28, "TL": 23, "TN": 24, "TR": 26, "UA": 29,
    "VA": 22, "VG": 24, "XK": 20, "YE": 30,
}  # fmt: skip

_NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)

_REGON_WEIGHTS = {
    9: (8, 9, 2, 3, 4, 5, 6, 7),
    14: (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8),
}


def is_base58check(text: str) -> bool:
    """Whether `text` is a 25-byte Base58Check payload whose tail is its digest.

    That is the shape of a legacy or pay-to-script Bitcoin address: a version
    byte, a twenty-byte hash and four bytes of double SHA-256 over the rest.
    """
    number = 0
    for char in text:
        index = _BASE58.find(char)
        if index < 0:
            return False
        number = number * 58 + index
    body = number.to_bytes((number.bit_length() + 7) // 8, "big")
    # Each leading `1` is a leading zero byte, which the integer cannot carry.
    leading = len(text) - len(text.lstrip("1"))
    raw = b"\x00" * leading + body
    if len(raw) != 25:
        return False
    digest = hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()
    return digest[:4] == raw[-4:]


def _polymod(values: list[int]) -> int:
    checksum = 1
    for value in values:
        top = checksum >> 25
        checksum = ((checksum & 0x1FFFFFF) << 5) ^ value
        for bit, coefficient in enumerate(_BECH32_GENERATOR):
            if (top >> bit) & 1:
                checksum ^= coefficient
    return checksum


def bech32_version(text: str) -> int | None:
    """The witness version of a mainnet Bech32 address, or None if it is not one.

    Version 0 addresses (``bc1q``) use the original Bech32 checksum; every
    later version, Taproot's ``bc1p`` among them, uses Bech32m. Mixed case is
    not an address: the specification allows all-lower or all-upper and nothing
    between, and a candidate that breaks that rule was never written by a wallet.
    """
    if text != text.lower() and text != text.upper():
        return None
    lowered = text.lower()
    prefix, separator, data = lowered.rpartition("1")
    if prefix != _MAINNET or not separator or len(data) < 6:
        return None
    try:
        values = [_BECH32.index(char) for char in data]
    except ValueError:
        return None
    version = values[0]
    if version > 16:
        return None
    expanded = [ord(char) >> 5 for char in prefix] + [0] + [ord(char) & 31 for char in prefix]
    expected = _BECH32_CONSTANT if version == 0 else _BECH32M_CONSTANT
    if _polymod(expanded + values) != expected:
        return None
    return version


def is_iban(text: str) -> bool:
    """Whether `text`, spaces or not, is an IBAN: known country, right length, mod-97."""
    compact = "".join(text.split()).upper()
    if not compact.isascii() or not compact.isalnum():
        return False
    if _IBAN_LENGTHS.get(compact[:2]) != len(compact) or not compact[2:4].isdigit():
        return False
    rearranged = compact[4:] + compact[:4]
    return int("".join(str(int(char, 36)) for char in rearranged)) % 97 == 1


def is_nip(digits: str) -> bool:
    """Whether ten digits are a Polish tax number: weighted sum mod 11 is the last.

    A remainder of ten has no digit to land on, so no check digit rescues it.
    """
    if len(digits) != 10 or not digits.isdigit():
        return False
    remainder = sum(int(d) * w for d, w in zip(digits[:9], _NIP_WEIGHTS, strict=True)) % 11
    return remainder != 10 and remainder == int(digits[9])


def is_regon(digits: str) -> bool:
    """Whether nine or fourteen digits are a Polish statistical number.

    Same weighted sum, with a remainder of ten written as zero.
    """
    weights = _REGON_WEIGHTS.get(len(digits))
    if weights is None or not digits.isdigit():
        return False
    remainder = sum(int(d) * w for d, w in zip(digits[:-1], weights, strict=True)) % 11
    return (0 if remainder == 10 else remainder) == int(digits[-1])


def is_onion(label: str) -> bool:
    """Whether 56 base32 characters are a version 3 onion service address.

    The label decodes to a public key, two bytes of checksum and a version
    byte; the checksum is SHA3-256 over a fixed prefix, the key and the
    version. Version 2 addresses are not accepted: the network stopped
    serving them in 2021, and a sixteen-character hash has no checksum.
    """
    try:
        raw = base64.b32decode(label.upper())
    except ValueError:
        return False
    if len(raw) != 35 or raw[34] != 3:
        return False
    digest = hashlib.sha3_256(b".onion checksum" + raw[:32] + raw[34:]).digest()
    return digest[:2] == raw[32:34]
