#!/usr/bin/python3

'''Assumptions till now:
1. Arrays are declared only as arr[10]int
and not initialized in the declaration itself.
2.
'''
import sys
import os
import ply.yacc as yacc

from lexer import *
from global_decls import *

root = ScopeTree(None, scopeName="global")
curr_scope = root

precedence = (
    ('right', 'AGN'),
    ('left', 'LOR'),
    ('left', 'LAND'),
    ('left', 'OR'),
    ('left', 'AND'),
    ('left', 'EQL', 'NEQ'),
    ('left', 'LSS', 'GTR', 'LEQ', 'GEQ'),
    ('left', 'SHL', 'SHR'),
    ('left', 'ADD', 'SUB'),
    ('left', 'MUL', 'QUO', 'REM'),
    ('right', 'NOT')
)

def p_start(p):
    '''start : SourceFile'''
    global source_root
    source_root = p[1]

def p_source_file(p):
    '''SourceFile : empty
                  | DeclList'''
    p[0] = p[1]

def p_decl_list(p):
    '''DeclList : TopLevelDecl
    			| TopLevelDecl DeclList'''
    if len(p) == 2:
        p[0] = p[1]
    else :
        p[0] =  p[1]
        p[0].code += p[2].code


def p_top_level_decl(p):
    '''TopLevelDecl : CommonDecl SEMCLN
    				| FuncDecl'''
    p[0] = p[1]

def p_common_decl(p):
    '''CommonDecl : CONST ConstDecl
                  | VAR VarDecl
                  | TYPE TypeDecl'''
    p[0] = container()
    p[0].code = p[2].code

def p_var_decl(p):
    '''VarDecl : DeclNameList Type
               | DeclNameList Type AGN ExprList'''
    global curr_scope
    p[0] = container()
    # incase type is declared to be some basic type e.g type new_int int;
    if p[2] in curr_scope.typeTable:
        p[2] = curr_scope.typeTable[p[2]]["type"]

    # TypeList for FuncDecl
    p[0].type = [p[2]]*len(p[1].value)

    if len(p)==5:
        # check length of decllist and ExprList
        if len(p[1].value) != len(p[4].value):
            raise_out_of_bounds_error(p[1].value,
                "different number of variables and expressions")
        p[0].code = p[4].code
        # all types on right must be same as Type
        for i in range(len(p[4].value)):
            if type(p[2])==container:
                typ = p[2].type
                base = p[2].extra["base"]
                length = p[2].extra["length"]
                p[1].value[i] = curr_scope.insert(p[1].value[i],
                    type=typ, base=base, length=length ,is_var=1)
            else:
                p[1].value[i] = curr_scope.insert(p[1].value[i], type=p[2], is_var=1)
            exp = p[4].value[i]
            if (p[2] != exp.type):
                # check if it is float = int case
                if exp.type=="int" and p[2]=="float":
                    exp.type = "float"
                    p[0].code.append(UOP(dst=p[1].value[i], op="inttofloat", arg1=exp.value))
                else:
                    raise_typerror(p[1].value,  "type mis-match in var declaration")
            else:
                p[0].code.append(ASN(dst=p[1].value[i], arg1=exp.value))
    else:
        for i in range(len(p[1].value)):
            if type(p[2])==container:
                if p[2].type=="array":
                    typ = "array"
                    base = p[2].extra["base"]
                    length = p[2].extra["length"]
                    size = curr_scope.sizeof(p[2])
                    p[1].value[i] = curr_scope.insert(p[1].value[i],type=typ,
                        base=base,length=length,size=size,is_var=1)
                elif p[2].type=="structure":
                    typ = "structure"
                    field_list = p[2].extra["field_list"]
                    size = curr_scope.sizeof(p[2])
                    p[1].value[i] = curr_scope.insert(p[1].value[i],type=typ,
                        field_list=field_list,size=size,is_var=1)
            else:
                size = curr_scope.sizeof(p[2])
                p[1].value[i] = curr_scope.insert(p[1].value[i],type=p[2],
                    size=size,is_var=1)

def p_decl_name_list(p):
    '''DeclNameList : Name
    				| DeclNameList COMMA Name'''
    if len(p)==2:
        p[0] = container(value=[p[1]])
    else:
        p[0] = p[1]
        p[0].value.append(p[3])

def p_const_decl(p):
    '''ConstDecl : DeclNameList Type AGN ExprList'''
    global curr_scope
    p[0] = container()
    # incase type is declared to be some basic type e.g type new_int int;
    if p[2] in curr_scope.typeTable:
        p[2] = curr_scope.typeTable[p[2]]["type"]
    p[0].code = p[4].code
    # all types on right must be same as Type
    for i in range(len(p[4].value)):
        # first insert
        p[1].value[i] = curr_scope.insert(p[1].value[i], type=p[2], is_var=0)
        exp = p[4].value[i]
        if (p[2] != exp.type):
            # check if it is float = int case
            if exp.type=="int" and p[2]=="float":
                exp.type = "float"
                p[0].code.append(UOP(dst=p[1].value[i], op="inttofloat", arg1=exp.value))
            else:
                raise_typerror(p[1].value,  "type mis-match in var declaration")
        else:
            p[0].code.append(ASN(dst=p[1].value[i], arg1=exp.value))

def p_type_decl_name(p):
    '''TypeDeclName : IDENT'''
    p[0] = p[1]

def p_type_decl(p):
    '''TypeDecl : TypeDeclName Type'''
    global curr_scope
    p[0] = container()
    if p[2] in curr_scope.typeTable:
        p[2] = curr_scope.typeTable[p[2]]["type"]
    curr_scope.insert_type(p[1], p[2])

def p_simple_stmt(p):
    '''SimpleStmt : Expr
                  | ExprList AGN ExprList
                  | ExprList DEFN ExprList'''
    # a,b = 1
    # a,b,c = 2,3,2
    # check if const is changed
    global curr_scope
    if len(p)==2:
        p[0] = p[1]
    else:
        if len(p[1].value) != len(p[3].value):
            raise_out_of_bounds_error(p[1].value+p[3].value,
                "error in short var decl/assignment")
        if p[2] == ":=" :
            pass
        elif p[2] == "=" :
            p[0] = container()
            for expr in p[1].value:
                if curr_scope.lookup_by_uniq_id(expr.value)["is_var"]==0:
                    raise_typerror(expr.value, ": Can't assign to a constant")
            p[0].code += p[1].code
            p[0].code += p[3].code
            for i in range(len(p[1].value)):
                expr = p[1].value[i]
                valexpr = p[3].value[i]
                if expr.type == valexpr.type :
                    if expr.type in set({"int","float","string"}) :
                        p[0].code.append(ASN(dst=expr.value,arg1=valexpr.value))
                elif (expr.type == "float") and (valexpr.type == "int") :
                    # new_place = curr_scope.new_temp()
                    p[0].code.append(UOP(dst=expr.value,op="inttofloat",arg1=valexpr.value))
                else :
                    raise_typerror(p[1].value, "in assignment : operands are different type")
                p[0].type = "void"

def p_stmt_block(p):
    '''StmtBlock : LCURL StartScope StmtList EndScope RCURL'''
    p[0] = p[3]

def p_block(p):
    '''Block : LCURL StmtList RCURL'''
    p[0] = p[2]

def p_for_header(p):
    '''ForHeader : OSimpleStmt SEMCLN OSimpleStmt SEMCLN OSimpleStmt
                 | OSimpleStmt'''
    p[0] = container()
    if len(p)==2 :
        p[0].extra["loop_type"] = "while"
        p[0].value = [container(),p[1],container()]
    else :
        p[0].extra["loop_type"] = "for"
        p[0].value = [p[1],p[3],p[5]]

def p_for_body(p):
    '''ForBody : ForHeader Block'''
    global curr_scope
    p[0] = container()
    block = p[2]
    initial,expr,update = p[1].value
    labelBegin = curr_scope.new_label()
    labelAfter = curr_scope.find_label("#forAfter")
    labelUpdate = curr_scope.find_label("#forUpdate")
    p[0].code += initial.code
    p[0].code.append(LBL(arg1=labelBegin))
    p[0].code += expr.code
    p[0].code.append(CBR(arg1=expr.value,op="==",arg2=0,dst=labelAfter))
    p[0].code += block.code
    p[0].code.append(LBL(arg1=labelUpdate))
    p[0].code += update.code
    # need to take care of break, continue - unlabelled
    p[0].code.append(CMD(op="goto",arg1=labelBegin))
    p[0].code.append(LBL(arg1=labelAfter))

def p_for_stmt(p):
    '''ForStmt : FOR beginFor ForBody endFor'''
    p[0] = p[3]
    p[0].type = "for_stmt"

def p_begin_for(p):
    '''beginFor :'''
    global curr_scope
    curr_scope = curr_scope.makeChildren()
    labelAfter = curr_scope.new_label()
    labelUpdate = curr_scope.new_label()
    curr_scope.insert_label(id="#forAfter",value=labelAfter)
    curr_scope.insert_label(id="#forUpdate",value=labelUpdate)

def p_end_for(p):
    '''endFor :'''
    global curr_scope
    curr_scope = curr_scope.parent

def p_if_stmt(p):
    '''IfStmt : IF Expr StmtBlock
              | IF Expr StmtBlock ElseStmt
              | IF Expr StmtBlock ElifList ElseStmt'''
    global curr_scope
    if len(p)==4 :
        labelAfter = curr_scope.new_label()
        p[0] = p[2]
        p[0].code.append(CBR(arg1=p[2].value,op="==",arg2=0,dst=labelAfter))
        p[0].code += p[3].code
        p[0].code.append(LBL(arg1=labelAfter))
    elif len(p)==5 :
        labelElse = curr_scope.new_label()
        labelAfter = curr_scope.new_label()
        p[0] = p[2]
        p[0].code.append(CBR(arg1=p[2].value,op="==",arg2=0,dst=labelElse))
        p[0].code += p[3].code
        p[0].code.append(CMD(op="goto",arg1=labelAfter))
        p[0].code.append(LBL(arg1=labelElse))
        p[0].code += p[4].code
        p[0].code.append(LBL(arg1=labelAfter))
    else :
        labelAfter = curr_scope.new_label()
        # If
        labelFalse = curr_scope.new_label()
        p[0] = p[2]
        p[0].code.append(CBR(arg1=p[2].value,op="==",arg2=0,dst=labelFalse))
        p[0].code += p[3].code
        p[0].code.append(CMD(op="goto",arg1=labelAfter))
        p[0].code.append(LBL(arg1=labelFalse))
        # ElifList
        for expr,block in p[4].value :
            labelFalse = curr_scope.new_label()
            p[0].code += expr.code
            p[0].code.append(CBR(arg1=expr.value,op="==",arg2=0,dst=labelFalse))
            p[0].code += block.code
            p[0].code.append(CMD(op="goto",arg1=labelAfter))
            p[0].code.append(LBL(arg1=labelFalse))
        # Else
        p[0].code += p[5].code
        p[0].code.append(LBL(arg1=labelAfter))

def p_else_if_list(p):
    '''ElifList : ElifStmt
                | ElifList ElifStmt'''
    if len(p)==2 :
        p[0] = container()
        p[0].value = [ p[1].value ]
    else :
        p[0] = p[1]
        p[0].value.append(p[2].value)

def p_else_if(p):
    '''ElifStmt : ELIF Expr StmtBlock'''
    p[0] = container()
    p[0].value = [p[3],p[4]]

def p_else_stmt(p):
    '''ElseStmt : ELSE StmtBlock'''
    p[0] = p[2]

def p_type(p):
    '''Type : Name
			| StructType
			| ArrayType
            | PtrType
			| LPRN Type RPRN'''
    if len(p)==2:
        p[0] = p[1]
    else:
        p[0] = p[2]

def p_other_type(p):
    '''OtherType : ArrayType
				 | PtrType
				 | StructType'''
    p[0] = p[1]

def p_array_type(p):
    '''ArrayType : LSQR Expr RSQR Type'''
    p[0] = container()
    p[0].type = "array"
    p[0].extra["length"] = p[2].value
    p[0].extra["base"] = p[4]

def p_struct_type(p):
    '''StructType : STRUCT LCURL StructDeclList OSemi RCURL'''
    # StructDeclList is a dictionary {ident:container(type=)}
    p[0] = container(type="structure")
    if len(p)==6:
        p[0].extra["field_list"] = p[3]
        # example: type = p[0].extra["field_list"]["field_name"].type

def p_func_decl(p):
    '''FuncDecl : FUNC IDENT beginFunc Parameters FuncRes FuncBody endFunc'''
    global curr_scope
    if p[6] is None :
        if not curr_scope.lookup(p[2]) :
            curr_scope.insert(p[2], type="func", arg_list=p[4].type,
                ret_type=p[5].type, is_var=0)
        else :
            raise_typerror(p[2], "identifier type mismatch/ function redeclared")
        if p[4].code :
            raise_general_error(p[2], "Syntax error")
    else :
        lookup_result =  curr_scope.lookup(p[2])
        if lookup_result :
            if lookup_result["is_var"] :
                raise_typerror(p[2], "Function Defined multiple times")
        curr_scope.insert(p[2], type="func", arg_list=p[4].type,ret_type=p[5].type, is_var=1)
        p[0] = container()
        p[0].code.append(LBL(arg1=p[2]))
        p[0].code.append(CMD(op="BeginFunc",arg1=p[7]))
        p[0].code += p[4].code
        p[0].code += p[6].code
        p[0].code.append(OP(op="EndFunc"))

def p_begin_func(p):
    '''beginFunc :'''
    global curr_scope
    curr_scope = curr_scope.makeChildren()
    curr_scope.offset = 0

def p_parameters(p):
    '''Parameters : LPRN RPRN
                  | LPRN ParamList RPRN'''
    if len(p)==3 :
        p[0] = container()
        p[0].type = list()
    else :
        p[0] = p[2]

def p_param_list(p):
    '''ParamList : dVarDecl
                 | ParamList COMMA dVarDecl'''
    if len(p)==2 :
        p[0] = p[1]
    else :
        p[0] = p[1]
        p[0].type += p[3].type
        p[0].code += p[3].code

def p_dvar_decl(p):
    '''dVarDecl : Type
                | VarDecl'''
    if str(p.slice[1]) == "Type" :
        p[0] = container()
        p[0].type = [p[1]]
    else :
        p[0] = p[1]
    # print(p[1].type)

def p_func_body(p):
    '''FuncBody : SEMCLN
                | Block'''
    if p[1] == ";" :
        p[0] = None
    else :
        p[0] = p[1]

def p_func_res(p):
    '''FuncRes : empty
               | Type'''
    global curr_scope
    p[0] = container()
    if str(p.slice[1]) == "empty" :
        p[0].type = None
        curr_scope.insert_type("#return",None)
    else :
        p[0].type = p[1]
        curr_scope.insert_type("#return",p[1])

def p_end_func(p):
    '''endFunc :'''
    global curr_scope
    offset = curr_scope.temp_offset
    p[0] = offset
    # offset gives you the total space used by any (scope+it's scildren scopes)
    curr_scope = curr_scope.parent

def p_struct_decl_list(p):
    '''StructDeclList : StructDecl
                      | StructDeclList SEMCLN StructDecl'''
    # StructDeclList is a dictionary {ident:container(type=type, size=)}
    global curr_scope
    if len(p)==2:
        p[0] = {}
        for field_name in p[1].value:
            p[0][field_name] = container(type=p[1].type, size=curr_scope.sizeof(p[1].type))
    else:
        p[0] = p[1]
        for field_name in p[3].value:
            p[0][field_name] = container(type=p[3].type, size=curr_scope.sizeof(p[3].type))

def p_struct_decl(p):
    '''StructDecl : FieldList Type'''
    # consider only the first rule
    # FieldList is a list
    p[0] = container()
    p[0].value = p[1]
    p[0].type = p[2]

def p_label_name(p):
    '''LabelName : NewName'''
    global curr_scope
    curr_scope.insert(p[1], type="label", is_var=0)
    p[0] = p[1]

def p_new_name(p):
    '''NewName : IDENT'''
    p[0] = p[1]

def p_field_name(p):
    '''FieldName : IDENT'''
    p[0] = p[1]

def p_ptr_type(p):
    '''PtrType : MUL Type'''
    # ptrType is a object
    p[0] = container()
    p[0].type = "pointer"
    p[0].extra["base"] = p[2]
    p[0].value = "*"+p[2]

def p_ocomma(p):
    '''OComma : empty
              | COMMA'''

def p_osemi(p):
    '''OSemi : empty
             | SEMCLN'''

def p_osimple_stmt(p):
    '''OSimpleStmt : empty
                   | SimpleStmt'''
    p[0] = p[1]

def p_oexpr(p):
    '''OExpr : empty
             | Expr'''
    p[0] = p[1]

def p_expr_list(p):
    '''ExprList : Expr
                | ExprList COMMA Expr'''
    if len(p)==2:
        p[0] = container()
        p[0].value = [p[1]]
        p[0].code = p[1].code
    else:
        p[0] = p[1]
        p[0].value.append(p[3])
        p[0].code += p[3].code

def p_basic_lit(p):
    '''BasicLit : INTEGER_LIT
                | FLOAT_LIT
                | STRING_LIT'''
    if type(p[1]) == int:
        p[0] = container(type="int", value=p[1])
    elif type(p[1]) == float:
        p[0] = container(type="float", value=p[1])
    else :
        p[0] = container(type="string", value=p[1])

def p_stmt_list(p):
    '''StmtList : empty
                | StmtList Stmt'''
    if len(p) == 2:
        p[0] = container()
    else :
        p[0] = p[1]
        p[0].code += p[2].code

def p_field_list(p):
    '''FieldList : FieldName
            	 | FieldList COMMA FieldName'''
    if len(p)==2:
        p[0] = [p[1]]
    else:
        p[0] = p[1]
        p[0].append(p[3])


def p_name(p):
    '''Name : IDENT'''
    p[0] = p[1]

def p_stmt(p):
    '''Stmt : StmtBlock
            | CommonDecl SEMCLN
            | NonDeclStmt'''
    p[0] = p[1]

def p_non_decl_stmt(p):
    '''NonDeclStmt : ForStmt
                   | IfStmt
                   | SimpleStmt SEMCLN
                   | BREAK SEMCLN
                   | CONTINUE SEMCLN
                   | GOTO NewName SEMCLN
                   | RETURN OExpr SEMCLN
                   | LabelName COLON Stmt'''
    global curr_scope
    if len(p) == 2:
        p[0] = p[1]
    elif len(p) == 3 :
        p[0] = p[1]
    else :
        p[0] = container()
        if str(p.slice[1]) == "LabelName" :
            p[0].code.append(LBL(arg1=p[1]))
            p[0].code += p[3].code
        elif p[1] == "goto" :
            p[0].code.append(CMD(op="goto",arg1=p[2]))
        elif p[1] == "break" :
            # p[0].type = "break"
            brk_lbl = curr_scope.find_label("#forAfter")
            p[0].code.append(CMD(op="goto",arg1=brk_lbl))
        elif p[1] == "continue" :
            # p[0].type = "continue"
            cont_lbl = curr_scope.find_label("#forUpdate")
            p[0].code.append(CMD(op="goto",arg1=cont_lbl))
        else : # return
            # p[0].type = "return"
            p[0] = container()
            ret_type = curr_scope.typeTable["#return"]["type"]
            if ret_type == p[2].type :
                if ret_type is None :
                    p[0].code.append(OP(op="return"))
                else :
                    p[0].code += p[2].code
                    p[0].code.append(CMD(op="return",arg1=p[2].value))
            else :
                raise_typerror(p[1],"type mismatch")



def p_pexpr(p):
    '''PExpr : Name
             | BasicLit
             | FuncCall
             | CompositeLit
             | LPRN Expr RPRN
             | PExpr DOT IDENT
             | PExpr LSQR Expr RSQR'''
    # print("PExpr",p.__dict__)
    if len(p)==2 :
        if str(p.slice[1]) == "Name":
            p[0] = container()
            lookup_result = curr_scope.lookup(p[1])
            if lookup_result is not None:
                # p[0].value = p[1] #name is a string
                p[0].value = lookup_result["uniq_id"]
                p[0].type = lookup_result["type"]
            else:
                raise_general_error("undeclared variable: " + p[1])
        else :
            p[0] = p[1]
    elif len(p)==4 :
        if p[1] == "(" :
            p[0] = p[2]
        else : # struct access
            pass

def p_composite_lit(p):
	'''CompositeLit : OtherType LitVal'''

def p_lit_val(p):
	'''LitVal : LCURL RCURL
			  | LCURL ElementList OComma RCURL '''

def p_element_list(p):
	'''ElementList : KeyedElement
				   | ElementList COMMA KeyedElement'''

def p_keyed_element(p):
	'''KeyedElement : Element
					| FieldName COLON Element'''

def p_element(p):
	'''Element : Expr
			   | LitVal'''

def p_func_call(p):
    '''FuncCall : Name LPRN RPRN
    			| Name LPRN ExprList RPRN'''
    global curr_scope
    p[0] = container()
    lookup_result = curr_scope.lookup(p[1])
    if lookup_result is None:
        raise_general_error("undeclared function: " + p[1])
    if len(p)==4 :
        if lookup_result["ret_type"] is None :
            p[0].code.append(CMD(op="call",arg1=p[1]))
            p[0].type = "void"
        else :
            p[0].type = lookup_result["ret_type"]
            new_place = curr_scope.new_temp(lookup_result["ret_type"])
            p[0].code.append(UOP(dst=new_place,op="call",arg1=p[1]))
            p[0].value = new_place
    else :
        p[0].code += p[3].code
        type_list = lookup_result["arg_list"]
        expr_list = p[3].value
        num_args = len(type_list)
        if num_args != len(expr_list) :
            raise_typerror(p[1],"No of arguments do not match")
        pop_size = 0
        for i in range(num_args-1,-1,-1):
            expr = expr_list[i]
            if type_list[i] != expr.type :
                raise_typerror(p[3],"type mismatch"+p[1])
            pop_size += curr_scope.sizeof(expr.type)
            p[0].code.append(CMD(op="push_param",arg1=expr.value))
        if lookup_result["ret_type"] is None :
            p[0].code.append(CMD(op="call",arg1=p[1]))
            p[0].value = None
            p[0].type = "void"
        else :
            p[0].type = lookup_result["ret_type"]
            new_place = curr_scope.new_temp(lookup_result["ret_type"])
            p[0].code.append(UOP(dst=new_place,op="call",arg1=p[1]))
            p[0].value = new_place
        p[0].code.append(CMD(op="pop_param",arg1=pop_size))

def p_expr(p):
    '''Expr : UExpr
            | Expr LOR Expr
            | Expr LAND Expr
            | Expr EQL Expr
            | Expr NEQ Expr
            | Expr LSS Expr
            | Expr GTR Expr
            | Expr LEQ Expr
            | Expr GEQ Expr
            | Expr OR Expr
            | Expr QUO Expr
            | Expr REM Expr
            | Expr SHL Expr
            | Expr SHR Expr
            | Expr ADD Expr
            | Expr SUB Expr
            | Expr MUL Expr
            | Expr AND Expr'''
    # check if undeclared variable is used
    global curr_scope
    if len(p) == 2 :
        p[0] = p[1]
    else:
        p[0] = container()
        p[0].code = p[1].code + p[3].code
        if p[1].type=="float" or p[3].type=="float":
            new_place = curr_scope.new_temp(type="float")
        else:
            new_place = curr_scope.new_temp(type="int")
        p[0].value = new_place
        # int only operators
        if p[2] in set({"||","&&","&","|","<<",">>","%"}):
            if p[1].type == "int" and p[3].type == "int":
                 p[0].code.append(BOP(dst=new_place,arg1=p[1].value,op=p[2],arg2=p[3].value))
                 p[0].type = "int"
            else :
                raise_typerror(p, "in expression : "
                    + p[2] + " operator takes int operands only" )
        # int or float
        else : #p[2] in set({"+","-","*","/","<",">",">=","<=","!=","=="}):
            if ((p[1].type == "int" and p[3].type == "int")
                    or (p[1].type == "float" and p[3].type == "float")) :
                p[0].code.append(BOP(dst=new_place,arg1=p[1].value,op=p[1].type+str(p[2]),arg2=p[3].value))
                p[0].type = p[1].type
                # print("BOP:int only",p[0].code[0])
            elif p[1].type == "int" and p[3].type == "float" :
                new_place1 = curr_scope.new_temp(type="float")
                p[0].code.append(UOP(dst=new_place1,op="inttofloat",arg1=p[1].value))
                p[0].code.append(BOP(dst=new_place,arg1=new_place1,op="float"+str(p[2]),arg2=p[3].value))
                p[0].type = "float"
            elif p[1].type == "float" and p[3].type == "int" :
                new_place1 = curr_scope.new_temp(type="float")
                p[0].code.append(UOP(dst=new_place1,op="inttofloat",arg1=p[3].value))
                p[0].code.append(BOP(dst=new_place,arg1=p[1].value,op="float"+str(p[2]),arg2=new_place1))
                p[0].type = "float"
            else :
                raise_typerror(p, "in expression : "
                    + p[2] + " operator takes int or float operands only" )

def p_uexpr(p):
    '''UExpr : PExpr
             | UnaryOp UExpr'''
    global curr_scope
    if len(p)==2:
        p[0] = p[1]
    else:
        p[0] = p[2]
        if p[1] != "+" :
            new_place = curr_scope.new_temp(type=p[2].type)# TEMP:
            p[0].value = new_place
            if (p[1] == "!") :
                if p[2].type == "int" :
                    p[0].code.append(UOP(dst=new_place,
                        op=p[1],arg1=p[2].value))
                    p[0].type = "int"
                else :
                    raise_typerror(p, "in unary expression : " + p[1]
                        + " operator takes int operands only" )
            elif p[1] == "-" :
                if (p[2].type == "int") or (p[2].type == "float") :
                    p[0].code.append(UOP(dst=new_place,
                        op=p[1],arg1=p[2].value))
                    p[0].type = p[2].type
                else :
                    raise_typerror(p, "in unary expression : " + p[1]
                        + " operator takes int or float operands only" )
            elif p[1] == "*" :
                if p[2].type == "pointer" :
                    p[0].code.append(UOP(dst=new_place,
                        op=p[1],arg1=p[2].value))
                    p[0].type = p[2].extra["base"].type
                    p[0].extra = p[2].extra["base"].extra
                else :
                    raise_typerror(p, "in unary expression : " + p[1]
                        + " operator takes pointer type operands only" )
            else : # address of -> &
                    p[0].code.append(UOP(dst=new_place,
                        op=p[1],arg1=p[2].value))
                    p[0].type = "pointer"
                    p[0].extra["base"] = p[2]

def p_unary_op(p):
    '''UnaryOp : ADD
               | SUB
               | NOT
               | MUL
               | AND'''
    p[0] = p[1]

def p_empty(p):
    '''empty : '''
    p[0] = container()

def p_start_scope(p):
    '''StartScope : empty'''
    global curr_scope
    curr_scope = curr_scope.makeChildren()

def p_end_scope(p):
    '''EndScope : empty'''
    global curr_scope
    offset_used_by_child = curr_scope.temp_offset
    curr_scope = curr_scope.parent
    curr_scope.temp_offset += offset_used_by_child

def p_error(p):
    global curr_scope
    print(p)
    exit(-1)

parser = yacc.yacc()


with open("test.go", "r") as f:
    data = f.read()
result = parser.parse(data)

three_ac = print_scopeTree(root,source_root,flag=False)
print("-"*20 + "START 3AC" + "-"*20)
print(three_ac)
print("-"*21 + "END 3AC" + "-"*21)
