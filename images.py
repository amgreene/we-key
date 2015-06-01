import cgi
import codecs
import collections
import datetime
import json
import re
import os
import hashlib

from conf import conf
from util import *


def generate_file_hash(path):
    BUF_SIZE = 65536
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


image_extensions = [
    'jpg', 'jpeg',
    'tif', 'tiff',
    'png',
    'gif',
]


def generate_index_file():
    index_file = data_open("hashes.txt", "w")

    # to do -- skip non-media file types
    # to do -- utf8 escape the values so json will be ok?
    for (dir_path, dir_names, file_names) in os.walk(
            unicode(conf['img_dir'])):
        for file_name in file_names:
            extension = file_name.split('.')[-1].lower()
            if not extension in image_extensions:
                continue
            abs_path = os.path.normpath(os.path.join(dir_path, file_name))
            rel_path = os.path.relpath(abs_path, conf['img_dir'])
            generated_hash = generate_file_hash(abs_path)
            index_file.write(generated_hash + '\t')
            index_file.write(rel_path)
            index_file.write('\n')


def find_image_by_hashlet(hashlet):
    index_file = data_open("hashes.txt")
    for line in index_file:
        if line.startswith(hashlet):
            # strip newline, extract relative path
            return line[:-1].split('\t')[1]


def get_abs_image_path(rel_path):
    return os.path.join(conf['img_dir'], rel_path)


if __name__ == "__main__":
    generate_index_file()
