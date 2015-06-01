conf = {
    'ga_key': 'Put your Google Analytics key here',
    'img_dir': '',
    'data_dir': '',
    'web_stage_dir': '',
    'im_convert_path': r'c:\Program Files\ImageMagick-6.9.1-Q16\convert.exe',
}

import os
if os.path.exists('conf_local.py'):
    from conf_local import conf_local
    for (k, v) in conf_local.items():
        conf[k] = v
