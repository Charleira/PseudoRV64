"""Ponto de implementação das regras declarativas do enunciado."""
from ast_nodes import IntLiteral, BoolLiteral, IdentifierExpr, UnaryExpr, UnaryOperator, BinaryExpr, BinaryOperator, CallExpr
from patterns import Rule, Pattern, REG, IMM12, POW2, imm12, pow2, Need, neg_imm12, COND, Args, EFFECT

#RULES IMPLEMETNADAS
#Literal inteiro com sinal ou bool para REG, com Li. 1
#Identificador para REG, reutilizando o VReg do símbolo. 0
#Literal elegível para IMM12 ou POW2, sem instrução. 0
#Negação aritmética de REG para REG, com Neg. 1
#Aritmética geral de dois REG para REG. 1
#Soma REG/IMM12 ou IMM12/REG, com Addi. 1
#Subtração REG menos literal cujo oposto cabe no imediato, com Addi. 1
#Multiplicação REG/POW2 ou POW2/REG, com Slli. 1
#Menor ou maior de dois REG para REG, com Slt. 1
#Menor ou igual, maior ou igual para REG, com Slt e Seqz. 2
#Igualdade/desigualdade para REG, com Xor e Seqz/Snez. 2
#Comparação de dois REG para COND, branch direto e Jump. 2
#Negação lógica de REG para REG, com Seqz. 1
#Negação lógica de COND para COND, invertendo destinos. 0
#&&/|| de dois COND para COND. 0
#&&/|| de dois COND para REG, com duas Li e um Jump. 3
#Literal bool para COND, com Jump. 1
#Identificador bool para COND, com branch e Jump. 2
#Chamada com argumentos REG para REG ou EFFECT, com Call. 1
#Chamada bool com argumentos REG para COND, com chamada e desvios. 3




def catalogue():
    """Codifique o catálogo do enunciado com Rule e Pattern."""

    #Lista que vai armazenar todas as regras do catálogo, lista necessária
    rules = []



    rules.append(
        Rule(
            #nome dele
            name="int_reg",
            #o que espera sair
            result=REG,
            #Pattern: esse precisei de ajuda para entender, mas
            #ele serve para descrever quais características 
            #uma expressão precisa ter para que determinada regra possa ser aplicada
            #Pattern fala as características a expressão precisa ter
            #kind=IntLiteral indica que aceitamos nós da AST do tipo IntLiteral
            pattern=Pattern(kind=IntLiteral),
            #custo
            cost=1,
            #armazena tipo de função
            action="literal_reg"
        )
    )

    #Literal booleano para REG, Li de custo 1.
    rules.append(
        Rule(
            name="bool_reg",
            result=REG,
            pattern=Pattern(kind=BoolLiteral),
            cost=1,
            action="literal_reg"
        )
    )
    #Identificador para REG, reutilizando o VReg do símbolo.
    rules.append(
        Rule(
            name="identifier_reg",
            result=REG,
            pattern=Pattern(kind=IdentifierExpr),
            cost=0,
            action="identifier_reg"
        )
    )


    #Literal elegível para IMM12 ou POW2, sem instrução. 0
    #Literal que cabe em um imediato de 12 bits
    rules.append(
        Rule(
            name="literal_imm12",
            result=IMM12,
            pattern=Pattern(predicate=imm12),
            cost=0,
            action="literal_imm12"
        )
    )
    #Literal que representa uma potência de 2
    rules.append(
        Rule(
            name="literal_pow2",
            result=POW2,
            pattern=Pattern(predicate=pow2),
            cost=0,
            action="literal_pow2"
        )
    )


    #Negação aritmética de REG para REG, com Neg. 1
    rules.append(
        Rule(
            name="negate_reg",
            result=REG,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NEGATE,
                children=(Need(REG),)
            ),
            cost=1,
            action="negate_reg"
        )
    )
    #Aritmética geral de dois REG para REG. 1
    #lista com as operações aritméticas, para não precisar criar uma regra para cada uma
    #cada tupla guarda o operador, nome da regra e ação
    arithmetic_operations = [
        (BinaryOperator.ADD, "add_reg", "add_reg"),
        (BinaryOperator.SUBTRACT, "sub_reg", "sub_reg"),
        (BinaryOperator.MULTIPLY, "mul_reg", "mul_reg"),
        (BinaryOperator.DIVIDE, "div_reg", "div_reg"),
        (BinaryOperator.REMAINDER, "rem_reg", "rem_reg"),
    ]

    for operator, name, action in arithmetic_operations:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG))
                ),
                cost=1,
                action=action
            )
        )


    #Soma REG/IMM12 ou IMM12/REG, com Addi 1
    #soma com imediato, podendo estar na esquerda ou direita
    rules.append(
        Rule(
            name="add_imm_right",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.ADD,
                children=(Need(REG), Need(IMM12))
            ),
            cost=1,
            action="add_imm_right"
        )
    )
    rules.append(
        Rule(
            name="add_imm_left",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.ADD,
                children=(Need(IMM12), Need(REG))
            ),
            cost=1,
            action="add_imm_left"
        )
    )

    #Subtração REG menos literal cujo oposto cabe no imediato, com Addi. 1  
    rules.append(
        Rule(
            name="sub_imm",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.SUBTRACT,
                children=(
                    Need(REG),
                    Pattern(predicate=neg_imm12)
                )
            ),
            cost=1,
            action="sub_imm"
        )
    )

    #Multiplicação REG/POW2 ou POW2/REG, com Slli. 1
    #POW2 = Potência de dois
    rules.append(
        Rule(
            name="mul_pow2_right",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.MULTIPLY,
                children=(Need(REG), Need(POW2))
            ),
            cost=1,
            action="mul_pow2_right"
        )
    )

    rules.append(
        Rule(
            name="mul_pow2_left",
            result=REG,
            pattern=Pattern(
                kind=BinaryExpr,
                operator=BinaryOperator.MULTIPLY,
                children=(Need(POW2), Need(REG))
            ),
            cost=1,
            action="mul_pow2_left"
        )
    )

    #Menor ou maior de dois REG para REG, com Slt. 1
    #comparações de menor e maior, usando Slt
    comparison_operations = [
        (BinaryOperator.LESS, "less_reg", "less_reg"),
        (BinaryOperator.GREATER, "greater_reg", "greater_reg"),
    ]

    for operator, name, action in comparison_operations:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG))
                ),
                cost=1,
                action=action
            )
        )  

    #Menor ou igual, maior ou igual para REG, com Slt e Seqz. 2
    comparison_equal_operations = [
        (BinaryOperator.LESS_EQUAL, "less_equal_reg", "less_equal_reg"),
        (BinaryOperator.GREATER_EQUAL, "greater_equal_reg", "greater_equal_reg"),
    ]

    for operator, name, action in comparison_equal_operations:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG))
                ),
                cost=2,
                action=action
            )
        ) 


    #Igualdade/desigualdade para REG, com Xor e Seqz/Snez. 2
    equality_operations = [
        (BinaryOperator.EQUAL, "equal_reg", "equal_reg"),
        (BinaryOperator.NOT_EQUAL, "not_equal_reg", "not_equal_reg"),
    ]

    for operator, name, action in equality_operations:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG))
                ),
                cost=2,
                action=action
            )
        )

    #Comparação de dois REG para COND, branch direto e Jump. 2
    #as comparações que geram desvios diretamente, sem guardar o resultado em REG
    condition_operations = [
        (BinaryOperator.LESS, "less_cond", "less_cond"),
        (BinaryOperator.LESS_EQUAL, "less_equal_cond", "less_equal_cond"),
        (BinaryOperator.GREATER, "greater_cond", "greater_cond"),
        (BinaryOperator.GREATER_EQUAL, "greater_equal_cond", "greater_equal_cond"),
        (BinaryOperator.EQUAL, "equal_cond", "equal_cond"),
        (BinaryOperator.NOT_EQUAL, "not_equal_cond", "not_equal_cond"),
    ]

    for operator, name, action in condition_operations:
        rules.append(
            Rule(
                name=name,
                result=COND,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(REG), Need(REG))
                ),
                cost=2,
                action=action
            )
        )

    #Negação lógica de REG para REG, com Seqz. 1
    rules.append(
        Rule(
            name="not_reg",
            result=REG,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NOT,
                children=(Need(REG),)
            ),
            cost=1,
            action="not_reg"
        )
    )

    #Negação lógica de COND para COND, invertendo destinos. 0
    rules.append(
        Rule(
            name="not_cond",
            result=COND,
            pattern=Pattern(
                kind=UnaryExpr,
                operator=UnaryOperator.NOT,
                children=(Need(COND),)
            ),
            cost=0,
            action="not_cond"
        )
    )

    #&&/|| de dois COND para COND. 0
    logical_operations = [
        (BinaryOperator.LOGICAL_AND, "and_cond", "and_cond"),
        (BinaryOperator.LOGICAL_OR, "or_cond", "or_cond"),
    ]

    for operator, name, action in logical_operations:
        rules.append(
            Rule(
                name=name,
                result=COND,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(COND), Need(COND))
                ),
                cost=0,
                action=action
            )
        )

    #&&/|| de dois COND para REG, com duas Li e um Jump. 3
    logical_reg_operations = [
        (BinaryOperator.LOGICAL_AND, "and_reg", "and_reg"),
        (BinaryOperator.LOGICAL_OR, "or_reg", "or_reg"),
    ]

    for operator, name, action in logical_reg_operations:
        rules.append(
            Rule(
                name=name,
                result=REG,
                pattern=Pattern(
                    kind=BinaryExpr,
                    operator=operator,
                    children=(Need(COND), Need(COND))
                ),
                cost=3,
                action=action
            )
        )

    #Literal bool para COND, com Jump. 1
    rules.append(
        Rule(
            name="bool_cond",
            result=COND,
            pattern=Pattern(kind=BoolLiteral),
            cost=1,
            action="bool_cond"
        )
    )

    #Identificador bool para COND, com branch e Jump. 2
    rules.append(
        Rule(
            name="identifier_cond",
            result=COND,
            pattern=Pattern(
                kind=IdentifierExpr
            ),
            cost=2,
            action="identifier_cond"
        )
    )

    #Chamada com argumentos REG para REG ou EFFECT, com Call. 1
    call_operations = [
        (REG, "call_reg", "call_reg"),
        (EFFECT, "call_effect", "call_effect"),
    ]

    for result, name, action in call_operations:
        rules.append(
            Rule(
                name=name,
                result=result,
                pattern=Pattern(
                    kind=CallExpr,
                    children=(Args(REG),)
                ),
                cost=1,
                action=action
            )
        )

    #Chamada bool com argumentos REG para COND, com chamada e desvios. 3
    rules.append(
        Rule(
            name="call_cond",
            result=COND,
            pattern=Pattern(
                kind=CallExpr,
                children=(Args(REG),)
            ),
            cost=3,
            action="call_cond"
        )
    )

    return rules
    raise NotImplementedError("implemente o catálogo")
