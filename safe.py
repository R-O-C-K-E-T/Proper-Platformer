import ast

# Despite what this module is called, I've got no clue if this is safe. Use at own peril
bannedNodes = set([ast.Import, ast.ClassDef, ast.Raise, ast.Try, ast.ExceptHandler])
bannedNames = set(['__import__','open', 'getattr','setattr','locals','globals','input',#print',
                   '__name__','__qualname__','__mro__','__dict__','__class__','mro','vars',
                   '__module__','__code__','__closure__','__kwdefaults__','__func__',
                   '__bases__','__subclasses__','eval','exec','compile','__builtins__'])

def validate(string):
    val = ast.parse(string)
    for node in ast.walk(val):
        if type(node) in bannedNodes:
            return node.lineno, node.col_offset
        if type(node) == ast.Name:
            if node.id in bannedNames:
                return node.lineno, node.col_offset
