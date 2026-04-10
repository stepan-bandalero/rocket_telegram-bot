import random
import string


def generate_gift_promo_code(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(random.choices(alphabet, k=length))
