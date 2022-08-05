import random
import string


def randomised_password():
    # returns a randomised 8 digit password for players to enter if they want to join a league
    letters = string.ascii_lowercase
    rand_pword = ''.join(random.choice(letters) for i in range(8))
    return rand_pword
