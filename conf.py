conf = {
    'ga_key': 'Put your Google Analytics key here',
    'img_dir': '',
    'data_dir': '',
}

import os
if os.path.exists('conf_local.py'):
    from conf_local import conf_local
    print "Importing conf_local"
    for (k, v) in conf_local.items():
        print k, v
        conf[k] = v
