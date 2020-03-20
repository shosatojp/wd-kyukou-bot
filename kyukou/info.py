from datetime import datetime
import os
isinpackage = not __name__ in ['info', '__main__']
if isinpackage:
    from .db import get_collection
    from . import util
else:
    from db import get_collection
    import util


def create_md():
    md = '<style>.markdown-section{max-width: unset;}</style>\n\n'
    md += '# 過去の休講情報一覧\n\n'
    md += '最終更新\\: '+datetime.now().strftime("%Y年%m月%d日 %H時%M分%S秒")+'\n\n'
    md += '|日付|時限|時間割コード|対象|教科|教員|備考|\n'
    md += '|---|---|---|---|---|---|---|\n'
    lectures = get_collection('lectures')
    syllabus = get_collection('syllabus')
    for lecture in lectures.find({}).sort('date', -1):
        class_nums = lecture.get("class_nums", [])
        syllabus_links = list(map(lambda class_num: util.Just(syllabus.find_one({"class_num": class_num})).url(), class_nums))
        subject = lecture.get('subject')
        date = datetime.fromtimestamp(lecture.get("date"))
        md += '|' + '|'.join([
            f'{date.strftime("%Y/%m/%d")} ({util.dayofweek[date.weekday()]})',
            ", ".join(map(str, lecture.get("periods"))),
            "・".join(map(lambda args: f"[{args[0]}]({args[1]})", zip(class_nums, syllabus_links))) if len(syllabus_links) else '不明',
            lecture.get("class", "-"),
            subject,
            lecture.get("teachers"),
            lecture.get("remark", "なし") or "-"
        ])+'|\n'

    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web/public/lectures.md'), 'wt', encoding='utf-8') as f:
        f.write(md)


if not isinpackage:
    create_md()
