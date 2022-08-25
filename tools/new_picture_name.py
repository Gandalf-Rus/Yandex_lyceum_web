import os
from random import randint


def give_picture_name():
    while 1 == 1:
        name = randint(1, 100000)
        if f"{name}.png" not in os.listdir("static/img"):
            break
    return f"static/img/{name}.png"
