from kvirt.config import Kbaseconfig
import os
import yaml

baseconfig = Kbaseconfig()
keywords = baseconfig.list_keywords()
kvirt_dir = os.path.dirname(baseconfig.__init__.__code__.co_filename)
with open(f'{kvirt_dir}/keywords.yaml') as f:
    keywords_info = yaml.safe_load(f)

for k in sorted(keywords):
    if k not in keywords_info or keywords_info[k] is None:
        print(k)
