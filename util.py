import codecs
import os


from conf import conf


def data_open(file_name, mode='r'):
    return codecs.open(os.path.join(conf['data_dir'], file_name), mode, 'utf-8')


