import cPickle as pickle
import UserDict

from rope.base.oi import objectdb


class MemoryDB(objectdb.FileDict):

    def __init__(self, project, persist=False):
        self.project = project
        self.persist = persist
        self._load_files()
        self.files = self

    def _get_persisted_file(self):
        resource = self.project.get_file(
            self.project.ropefolder.path + '/objectdb.pickle')
        return resource

    def _load_files(self):
        self._files = {}
        if self.persist:
            persisted = self._get_persisted_file()
            if persisted.exists():
                output = open(persisted.real_path, 'rb')
                self._files = pickle.load(output)
                output.close()

    def keys(self):
        return self._files.keys()

    def __contains__(self, key):
        return key in self._files

    def __getitem__(self, key):
        return FileInfo(self._files[key])

    def create(self, path):
        self._files[path] = {}

    def rename(self, file, newfile):
        if file not in self._files:
            return
        self._files[newfile] = self._files[file]
        del self[file]

    def __delitem__(self, file):
        del self._files[file]

    def sync(self):
        if self.persist:
            output = open(self._get_persisted_file().real_path, 'wb')
            pickle.dump(self._files, output)
            output.close()


class FileInfo(objectdb.FileInfo):

    def __init__(self, scopes):
        self.scopes = scopes

    def create_scope(self, key):
        self.scopes[key] = ScopeInfo()

    def keys(self):
        return self.scopes.keys()

    def __contains__(self, key):
        return key in self.scopes

    def __getitem__(self, key):
        return self.scopes[key]

    def __delitem__(self, key):
        del self.scopes[key]


class ScopeInfo(objectdb.ScopeInfo):

    def __init__(self):
        self.call_info = {}
        self.per_name = {}

    def get_per_name(self, name):
        return self.per_name.get(name, None)

    def save_per_name(self, name, value):
        self.per_name[name] = value

    def get_returned(self, parameters):
        return self.call_info.get(parameters, None)

    def get_call_infos(self):
        for args, returned in self.call_info.items():
            yield objectdb.CallInfo(args, returned)

    def add_call(self, parameters, returned):
        self.call_info[parameters] = returned

    def __getstate__(self):
        return (self.call_info, self.per_name)

    def __setstate__(self, data):
        self.call_info, self.per_name = data