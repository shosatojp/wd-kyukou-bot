
import glob
from bs4 import BeautifulSoup
import re
import os
isinpackage = not __name__ in ['syllabus', '__main__']
if isinpackage:
    from .db import get_collection
    from .util import find_index
else:
    from db import get_collection
    from util import find_index


def parse_when(src):
    dayofweek = '月火水木金土日'
    if len(src) > 0 and src[0] == '他':
        return {'type': 'other'}
    result = []
    for e in src.split(','):
        if len(e) > 1:
            i = find_index(dayofweek, e[0])
            if i > -1:
                result.append({'dayofweek': i, 'period': int(e[1])})
    return {'type': 'time', 'times': result}


def scrape_syllabus(html):
    doc = BeautifulSoup(html, 'html.parser')
    table = doc.select('tbody')[8]
    # url_src_re = re.compile(r"refer\('(\d+)','(\d+)','(\d+)'\);")
    result = []
    for tr in table.select('tr'):
        tds = tr.select('td')
        # URL
        url_src = tds[5].select_one('a').get('href').strip()
        # m = url_src_re.match(url_src)

        result.append({
            "semester": tds[1].text.strip(),
            "open": tds[2].text.strip(),
            "when": parse_when(tds[3].text.strip()),
            "class_num": tds[4].text.strip(),
            "subject": tds[5].text.strip(),
            "teachers": tds[6].text.strip(),
            "url": f"http://kyoumu.office.uec.ac.jp/syllabus/2019/${url_src}",
        })
    return result


def syllabus_all(_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)),'syllabus')):
    syllabus = get_collection('syllabus')
    for path in glob.glob(f'{_dir}/*'):
        with open(path, 'rt', encoding='utf-8') as f:
            for e in scrape_syllabus(f.read()):
                if not syllabus.find_one({'class_num': e.get('class_num')}):
                    print(e)
                    syllabus.insert_one(e)


if not isinpackage:
    syllabus_all()
