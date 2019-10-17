from functools import reduce
import time
import random
from pprint import pprint
isinpackage = not __name__ in ['procedure', '__main__']
if isinpackage:
    from .scheduler import add_task
    from .db import get_collection
    from .util import Just


def process(p, n):
    def wrapper(f):
        p.processes.append({
            "order": n,
            "func": f
        })

        def _wrapper():
            f(n)
        return _wrapper
    return wrapper


class Procedure():
    def __init__(self, oncondition, procedure_id, **kwargs):
        self.collection = {}
        self.processes = []
        self.oncondition = oncondition
        self.procedure_id = procedure_id
        self.info = {}
        self.kwargs = kwargs or {}

    def set_progress(self, _id, progress):
        self.collection[_id] = progress

    def get_progress(self, _id):
        progress = self.collection.get(_id)
        return -1 if progress == None else progress

    def set_info(self, _id, key, value):
        self.info[_id] = self.info.get(_id) or {}
        self.info[_id][key] = value

    def get_info(self, _id):
        return self.info.get(_id) or {}

    def run(self, _id, *args, **kwargs):
        if self.get_progress(_id)+1 >= len(self.processes):
            raise RuntimeError
        else:
            r = self.processes[self.get_progress(_id)+1]["func"](_id, *args, **kwargs)
            if self.get_progress(_id) == len(self.processes)-1:
                self.remove(_id)
            return r

    def check(self, _id, *args, **kwargs):
        if self.oncondition(_id, *args, **kwargs):
            return True
        else:
            return len(self.processes) > self.get_progress(_id) > -1

    def end(self, _id):
        self.remove(_id)

    def remove(self, _id):
        del self.collection[_id]
        if _id in self.info:
            del self.info[_id]


class ProcedureSelector():
    def __init__(self, *procedures):
        self.procedures = {}
        for procedure in procedures:
            self.procedures[procedure.procedure_id] = procedure
        self.current = {}

    def run(self, _id, *args, **kwargs):
        procedure_id = self.current.get(_id)
        if procedure_id and self.procedures[procedure_id].get_progress(_id) != -1:
            self.procedures[procedure_id].run(_id, *args, **kwargs)
            return True
        for k, procedure in self.procedures.items():
            if procedure.check(_id, *args, **kwargs):
                procedure.run(_id, *args, **kwargs)
                self.current[_id] = k
                return True
        return None

    def end(self, _id):
        del self.current[_id]
        for procedure in self.procedures.values():
            procedure.end(_id)

    def clear(self):
        for procedure in self.procedures.values():
            if hasattr(procedure, 'clear'):
                procedure.clear()


if isinpackage:

    class ProcedureDB(Procedure):
        def __init__(self, oncondition, procedure_id, timeout=3600, **kwargs):
            self.collection = get_collection('procedure')
            self.processes = []
            self.oncondition = oncondition
            self.procedure_id = procedure_id
            self.timeout = timeout
            self.kwargs = kwargs or {}
            add_task(60, self.clear)

        def set_progress(self, _id, progress):
            if not self.collection.update_one({'id': _id, 'procedure_id': self.procedure_id}, {
                    '$set': {
                        'progress': progress
                    }}).matched_count:
                self.collection.insert_one({'id': _id, 'procedure_id': self.procedure_id,
                                            'progress': progress,
                                            'expired_at': time.time()+self.timeout})

        def get_progress(self, _id):
            r = self.collection.find_one({'id': _id, 'procedure_id': self.procedure_id})
            return -1 if r == None else r.get('progress')

        def set_info(self, _id, key, value):
            self.collection.update_one({'id': _id, 'procedure_id': self.procedure_id}, {
                '$set': {
                    f'info.{key}': value
                }
            })

        def get_info(self, _id):
            return self.collection.find_one({'id': _id, 'procedure_id': self.procedure_id}).get('info') or {}

        def clear(self):
            self.collection.delete_many({'procedure_id': self.procedure_id,
                                         'expired_at': {'$lt': time.time()}})
            self.collection.delete_many({'progress': -1})

        def remove(self, _id):
            self.collection.delete_one({'id': _id, 'procedure_id': self.procedure_id})

    class ProcedureSelectorDB():
        selectors = []
        @staticmethod
        def clear_all():
            for s in ProcedureSelectorDB.selectors:
                s.clear()

        def __init__(self, *procedures):
            ProcedureSelectorDB.selectors.append(self)
            self.procedures = {}
            for procedure in procedures:
                self.procedures[procedure.procedure_id] = procedure
            self.current = get_collection('current_procedure')

        def run(self, _id, *args, **kwargs):
            procedure_id = Just(self.current.find_one({'id': _id})).procedure()
            if procedure_id and self.procedures[procedure_id].get_progress(_id) != -1:
                self.procedures[procedure_id].run(_id, *args, **kwargs)
                return True
            for k, procedure in self.procedures.items():
                if procedure.check(_id, *args, **kwargs):
                    procedure.run(_id, *args, **kwargs)
                    self.current.update({'id': _id}, {'procedure': k, 'id': _id, 'expired_at': time.time()+3600}, True)
                    return True
            return None

        def end(self, _id):
            self.current.delete_one({'id': _id})
            for procedure in self.procedures.values():
                procedure.end(_id)

        def clear(self):
            self.current.delete_many({'expired_at': {'$lt': time.time()}})
            for procedure in self.procedures.values():
                if hasattr(procedure, 'clear'):
                    procedure.clear()

        def get_description(self):
            return reduce(lambda i, p: i + f"【{p.kwargs.get('title','')}】: {p.kwargs.get('description','')}\n", self.procedures.values(), '')


if not isinpackage:
    p = Procedure(lambda id, *args: args[0] == 'mail', 'mail')
    @process(p, 0)
    def process0(id, args):
        print('0', id)
        p.set_info(id, 'day', 3)
        p.set_progress(id, 0)

    @process(p, 1)
    def process1(id, args):
        print('1', id, p.get_info(id))

        p.set_progress(id, 1)

    p2 = Procedure(lambda id, *args: args[0] == 'csv', 'csv')

    @process(p2, 0)
    def process20(id, args):
        print('p2', id)
        p2.set_progress(id, 0)

    ps = ProcedureSelector(p, p2)
    args = ['mail']
    ps.run('hoge', *args)
    ps.run('hige', *args)
    args = ['mail']
    ps.run('hige', *args)
    ps.run('hoge', *args)
else:
    __all__ = ["Procedure", "ProcedureDB", "process", "ProcedureSelector", "ProcedureSelectorDB"]
