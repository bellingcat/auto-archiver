import os

def mkdir_if_not_exists(folder):
    if not os.path.exists(folder):
        os.mkdir(folder)