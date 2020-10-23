import ast

# Despite what this module is called, I've got no clue if this is safe. Use at own peril
BANNED_NODES = set([ast.Import, ast.ClassDef, ast.Raise, ast.Try, ast.ExceptHandler])
BANNED_NAMES = set(['__import__','open', 'getattr','setattr','locals','globals','input',#print',
                   '__name__','__qualname__','__mro__','__dict__','__class__','mro','vars',
                   '__module__','__code__','__closure__','__kwdefaults__','__func__',
                   '__bases__','__subclasses__','eval','exec','compile','__builtins__'])

def validate(string):
    val = ast.parse(string)
    for node in ast.walk(val):
        if type(node) in BANNED_NODES:
            return node.lineno, node.col_offset
        if isinstance(node, ast.Name):
            if node.id in BANNED_NAMES:
                return node.lineno, node.col_offset
