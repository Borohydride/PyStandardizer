import sys
import inspect
import pickle
from io import StringIO, BytesIO

class Serializer:
    def __init__(self):
        self.type_registry = {}
        self.object_registry = {}
        self.object_id_counter = 0
        self.register_all_imported_types()

    def register_type(self, cls):
        self.type_registry[cls.__name__] = cls
        return cls

    def register_all_imported_types(self):
        for module_name, module in sys.modules.items():
            if module is None:
                continue
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if obj.__module__ == module_name:
                    self.register_type(obj)

    def serialize(self, obj):
        def _serialize(obj):
            if id(obj) in self.object_registry:
                return {'__ref__': self.object_registry[id(obj)]}
            if isinstance(obj, (int, float, str, bool, type(None))):
                return obj
            elif isinstance(obj, list) and hasattr(obj, '__dict__'):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__type__': type(obj).__name__,
                    '__bases__': [base.__name__ for base in type(obj).__bases__],
                    '__list__': [_serialize(item) for item in obj],
                    '__dict__': {key: _serialize(value) for key, value in obj.__dict__.items()}
                }
            elif isinstance(obj, dict) and hasattr(obj, '__dict__'):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__type__': type(obj).__name__,
                    '__bases__': [base.__name__ for base in type(obj).__bases__],
                    '__dict__': {key: _serialize(value) for key, value in obj.items()},
                    '__custom_dict__': True
                }
            elif isinstance(obj, list):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__list__': [_serialize(item) for item in obj]
                }
            elif isinstance(obj, dict):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__dict__': {key: _serialize(value) for key, value in obj.items()}
                }
            elif isinstance(obj, set):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {'__set__': [_serialize(item) for item in obj]}
            elif isinstance(obj, tuple):
                return {'__tuple__': [_serialize(item) for item in obj]}
            elif isinstance(obj, StringIO):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__StringIO__': obj.getvalue(),
                    '__StringIO_pos__': obj.tell()
                }
            elif isinstance(obj, BytesIO):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__BytesIO__': obj.getvalue().hex(),
                    '__BytesIO_pos__': obj.tell()
                }
            elif hasattr(obj, '__dict__'):
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {
                    '__type__': type(obj).__name__,
                    '__bases__': [base.__name__ for base in type(obj).__bases__],
                    '__dict__': {key: _serialize(value) for key, value in obj.__dict__.items()}
                }
            else:
                self.object_id_counter += 1
                obj_id = self.object_id_counter
                self.object_registry[id(obj)] = obj_id
                return {'__pickle__': pickle.dumps(obj).hex()}

        return _serialize(obj)

    def deserialize(self, data):
        self.object_registry = {}
        self.object_id_counter = 0

        def _deserialize(d):
            if isinstance(d, (int, float, str, bool, type(None))):
                obj = d
            elif isinstance(d, list):
                obj = []
                self.object_registry[self.object_id_counter] = obj
                self.object_id_counter += 1
                for item in d:
                    obj.append(_deserialize(item))
            elif isinstance(d, dict):
                if '__ref__' in d:
                    obj = self.object_registry[d['__ref__']]
                elif '__type__' in d and '__dict__' in d:
                    type_name = d['__type__']
                    bases_names = d.get('__bases__', [])
                    obj_dict = d['__dict__']
                    if type_name in self.type_registry:
                        cls = self.type_registry[type_name]
                        for base_name in bases_names:
                            if base_name in self.type_registry:
                                base_cls = self.type_registry[base_name]
                                cls = type(type_name, (cls, base_cls), {})
                        obj = cls.__new__(cls)
                        self.object_registry[self.object_id_counter] = obj
                        self.object_id_counter += 1
                        if '__list__' in d:
                            obj.extend(_deserialize(d['__list__']))
                        if '__dict__' in d and d.get('__custom_dict__', False):
                            for key, value in _deserialize(d['__dict__']).items():
                                obj[key] = value
                        else:
                            for key, value in obj_dict.items():
                                setattr(obj, key, _deserialize(value))
                    else:
                        raise TypeError(f"Unknown type {type_name}")
                elif '__set__' in d:
                    obj = set()
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                    for item in d['__set__']:
                        obj.add(_deserialize(item))
                elif '__tuple__' in d:
                    obj = tuple([_deserialize(item) for item in d['__tuple__']])
                elif '__StringIO__' in d:
                    string_io = StringIO(d['__StringIO__'])
                    string_io.seek(d['__StringIO_pos__'])
                    obj = string_io
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                elif '__BytesIO__' in d:
                    bytes_io = BytesIO(bytes.fromhex(d['__BytesIO__']))
                    bytes_io.seek(d['__BytesIO_pos__'])
                    obj = bytes_io
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                elif '__pickle__' in d:
                    obj = pickle.loads(bytes.fromhex(d['__pickle__']))
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                elif '__list__' in d:
                    obj = (_deserialize(d['__list__']))
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                elif '__dict__' in d:
                    obj = {}
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                    for key, value in _deserialize(d['__dict__']).items():
                        obj[key] = value
                else:
                    obj = {}
                    self.object_registry[self.object_id_counter] = obj
                    self.object_id_counter += 1
                    for key, value in d.items():
                        obj[key] = _deserialize(value)
            else:
                raise TypeError(f"Type {type(d)} is not deserializable")

            return obj

        return _deserialize(data)