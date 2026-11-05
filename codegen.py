"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ir import Context, ProgramIR, FunctionIR, Param


class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        #Ok, a gente tem essa descrição do arquivo
        #generate recebe um Program e devolve um ProgramIR. Erros léxicos, sintáticos
        #ou semânticos impedem essa chamada. Use as anotações symbol, scope e type existentes. Não refaça as análises ou altere a AST. Gere o mesmo programa repetidamente,
        #inclusive reutilizando o objeto CodeGenerator.
        programIR = ProgramIR()

        #cria a representação da função atual e adiciona ao programIR
        for function in program.functions:
            #capturar funções e coloca no programIR
            functionIR = FunctionIR(function)
            programIR.functions.append(functionIR)

            #guarda coisas como retradores, rótulos e símbolos. Testar
            self.context = Context(functionIR, programIR)

            #Percorrer cada parametro da função
            for index, parameter in enumerate(function.parameters):

                #recupera o símbolo associado ao parâmetro pela análise semântica anterior
                symbol = parameter.metadata["symbol"]

                #obtém ou cria se não tiver um registrador virtual symbol
                register = self.context.variable(symbol)

                #emite a instrução que RECEBE o parâmetro
                self.context.emit(
                    Param(register, index, origin=parameter.span)
                )

            #Percorre os comandos do corpo da função.
            self.statement(function.body)
        # Devolve o programa intermediário completo.
        return programIR
        raise NotImplementedError("implemente CodeGenerator.generate")

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        raise NotImplementedError("implemente seleção e emissão")

    def statement(self, node):
        """Traduza um comando ad hoc."""
        raise NotImplementedError("implemente comandos")
