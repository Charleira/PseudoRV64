"""Ponto de implementação das regras declarativas do enunciado."""
from ast_nodes import IntLiteral, BoolLiteral, IdentifierExpr, UnaryExpr, UnaryOperator, BinaryExpr, BinaryOperator
from patterns import Rule, Pattern, REG, IMM12, POW2, imm12, pow2, Need

#RULES IMPLEMETNADAS
#Literal inteiro com sinal ou bool para REG, com Li. 1
#Identificador para REG, reutilizando o VReg do símbolo. 0
#Literal elegível para IMM12 ou POW2, sem instrução. 0


def catalogue():
    """Codifique o catálogo do enunciado com Rule e Pattern."""

    #Lista que vai armazenar todas as regras do catálogo, lista necessária
    rules = []

    #Regra 1 macro, ela tem entrada 
    #Literal inteiro com sinal para REG, Li de c usto 1
    #Literal elegível para IMM12 ou POW2, sem instrução. 0 
    #Negação aritmética de REG para REG, com Neg. 1
    #Aritmética geral de dois REG para REG. 1

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

    return rules
    raise NotImplementedError("implemente o catálogo")
