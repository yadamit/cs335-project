class IfStmt(object):
    """IfStmt : IF Expr Block ElseOpt """

    def __init__(self, arg):
        self.condition = None
        self.block = None
        self.else_opt = None


global expr


class Expression(object):
    '''Expression : UnaryExpr | BinaryExpr'''

    def __init__(self):
        super(Expression, self)
        self._fields = []


global ast_imports
ast_imports = []

# global ast_expr = {  }

# possible scopes: package, global, functions, ....
global curr_scope
curr_scope = None
global scope_count
scope_count = 0

class ScopeTree:
    def __init__(self, parent, scopeName=None):
        self.children = []
        self.parent = parent
        self.symbolTable = {} #{"var": [type, size, value, offset]}
        if scopeName is None:
            global scope_count
            self.identity = {"name":scope_count}
            scope_count += 1
        else:
            self.identity = {"name":scopeName}
            scope_count += 1

    def insert(self, id, type, is_var=1):
        self.symbolTable[id] = [type, is_var]

    def makeChildren(self, childName=None):
        child = ScopeTree(self, childName)
        self.children.append(child)
        return child

    def lookup(self, id):
        if id in self.symbolTable:
            return self.symbolTable[id]
        else:
            return self.parent.lookup(id)


class container:
    def __init__(self, type=None, value=None):
        self.type = type
        self.value = value

def raise_typerror(p):
    print("Type error")
    print("\t p")
    exit(-1)
