import persistent
import ZODB.FileStorage

db = ZODB.DB('database.fs')


class User(persistent.Persistent):
    def __init__(self, id):
        self.id = id
        self.roles = None
        self.overwrites = {}
