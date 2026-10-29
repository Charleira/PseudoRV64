"""Construa um CFG auxiliar por função, preservando os nós da AST."""

from __future__ import annotations

import load_previous  # Disponibiliza os módulos das etapas anteriores.

from ast_nodes import Block, FunctionDecl, IfStmt, Stmt, WhileStmt, Assignment, CallStmt, PrintStmt, ReturnStmt, VarDecl, BoolLiteral
from cfg import BlockId, CFG, Jump, Branch, Return, ScopeExit


class CFGBuilder:
    def build(self, function: FunctionDecl) -> CFG:
        self.cfg = CFG(function)
        body_entry = self.cfg.new_block()
        self.cfg.terminate(self.cfg.entry, Jump(body_entry.id))
        continuation = self._build_block(function.body, body_entry.id)
        if continuation is not None:
            self.cfg.terminate(continuation, Jump(self.cfg.fallthrough_exit))
        return self.cfg

    def _build_block(self, block: Block, current: BlockId) -> BlockId | None:
        """Percorra um bloco da AST e devolva sua continuação normal.

        `current` identifica um bloco básico aberto. Comandos sequenciais
        permanecem nele. Comandos de controle podem mudar a continuação.
        None indica que os caminhos deste bloco não alcançam o próximo comando.
        """
        currentLocal = current

        #percorrer todos os statments armazenados
        for statment in block.statements:
            #verifica se o comando anterior terminou o fluxo normal, se sim, 
            #ele não alcança o próximo comando
            if currentLocal is None:
                break
            #manda o bloco atual para o build_Statment, nele resolveremos mais de manter o bloco e sua continuação
            currentLocal = self._build_statement(statment, currentLocal)
        #CORRIGIDO DE ERROO: e o bloco possui uma continuação normal,
        # registra que estamos saindo do escopo desse bloco
        if currentLocal is not None:

             #recupera o escopo associado ao bloco pela análise anterior
            scope = block.metadata["scope"]

            #adiciona a operação de saída de escopo
            self.cfg.blocks[currentLocal].operations.append(
                ScopeExit(scope)
            )
        return currentLocal


        

        raise NotImplementedError("implemente CFGBuilder._build_block")

    def _build_statement(self, statement: Stmt, current: BlockId) -> BlockId | None:
        """TODO: incorpore um comando ao CFG e devolva sua continuação normal."""
        #isso pode estar errado, vale a pena revisar depois
        #Verifica se o comando é um bloco que contém outros comandos
        if isinstance(statement, Block):
            return self._build_block(statement, current)
        #Verifica se o comando é if
        if isinstance(statement, IfStmt):
            return self._build_if(statement, current)
        #verifica se o comando é while
        if isinstance(statement, WhileStmt):
            return self._build_while(statement, current)
        #verifica se o comando e tem return
        #encerra o bloco atual
        if isinstance(statement, ReturnStmt):
            self.cfg.terminate(current, Return(statement))
            #Precisa de algum return para terminar
            return None
        #verificar se é uma declaração de variável, uma atribuição, uma chamada de func, ou impressão
        if isinstance(statement,(VarDecl, Assignment,CallStmt,PrintStmt)):
            #Adiciona o comando à lista de operações do bloco
            #Esses comandos não encerram o bloco nem criam ramificações
            #Essa parte da chamada para criação de novos elementos, tem que se mexer dps
            self.cfg.blocks[current].operations.append(statement)
            # Retorna o identificador do bloco atual, que pode recebermais comandos
            return current


        raise NotImplementedError("implemente CFGBuilder._build_statement")

    def _build_if(self, statement: IfStmt, current: BlockId) -> BlockId | None:
        """TODO: construa o fluxo da condicional e devolva sua continuação."""
        #IftrueBlock e IfFalseBlock - dois caminhos precisa
        #criação de um novo block vem do cfg, tem como criar chamando o próprio build?
        ifTrueBlock = self.cfg.new_block()

        # Constrói os comandos do caminho verdadeiro
        ifTrue = self._build_block(
            statement.then_block,
            ifTrueBlock.id
        )

        #verifica se tem um else
        if statement.else_block is not None:
            ifFalseBlock = self.cfg.new_block()

            #definindo o destino das condições, se tem else
            self.cfg.terminate(
                current, Branch(
                    statement.condition,
                    ifTrueBlock.id,
                    ifFalseBlock.id,
                )
            )
            
            # Constrói os comandos do caminho falso, igual o ifTrue
            ifFalse = self._build_block(
                statement.else_block,
                ifFalseBlock.id
            )
            #Se os dois caminhos terminam com return, então não há continuação após o if
            if ifTrue is None and ifFalse is None:
                return None

            #bloco para continuar a execução após o if
            restoBlock = self.cfg.new_block()

            #Se o caminho tem continuação, a gente continua
            if ifTrue is not None:
                self.cfg.terminate(
                    ifTrue,
                    Jump(restoBlock.id)
                )

            if ifFalse is not None:
                self.cfg.terminate(
                    ifFalse,
                    Jump(restoBlock.id)
                )

            #retorna o identificador do bloco de continuação
            return restoBlock.id


        #caso o else não tenha, agente vem direto criando o restoBlock
        restoBlock = self.cfg.new_block()

        # se condição for verdadeira executa if
        self.cfg.terminate(
            current,
            Branch(
                statement.condition,
                ifTrueBlock.id,
                restoBlock.id
            )
        )

        # Se o caminho verdadeiro não terminou com return,
        # conecta esse caminho ao bloco de continuação
        if ifTrue is not None:
            self.cfg.terminate(
                ifTrue,
                Jump(restoBlock.id)
            )

        #retorna o identificador do bloco de continuação
        return restoBlock.id



        raise NotImplementedError("implemente CFGBuilder._build_if")

    def _build_while(self, statement: WhileStmt, current: BlockId) -> BlockId | None:
        """TODO: construa o fluxo do laço e devolva sua continuação."""
        #bloco da condição do while
        condBlock = self.cfg.new_block()

        #bloco do while em sí
        whileBlock = self.cfg.new_block()

        #bloco do que vem depois do while, talvez renomear dps para restoBlock igual o do if
        #restoBlock = self.cfg.new_block()
        #CORRIGIDO ERRO:
        #Aconteceu um erro ao executar
        #Conecta o bloco atual ao bloco que verifica a condição
        #a gente precisa conectar eles pois o condBlock sempre ser checado
        self.cfg.terminate(
            current,
            Jump(condBlock.id)
        )
        #se não existir caminho falso, foi isso que quebrou quando eu sempre
        #assumia que o caminho tinha um restoBlock, agora esse é o lado que não existe
        #caminho falso e restoBlock vai ser criado dps
        if isinstance(statement.condition, BoolLiteral) and statement.condition.value:

            # é verdadeira, já se conecta direto com o corpo do WHilE
            self.cfg.terminate(
                condBlock.id,
                Jump(whileBlock.id)
            )

            #Cria o WhileTrue infinito co mos comandos que tão dentro dele
            whileTrue = self._build_block(
                statement.body,
                whileBlock.id
            )

            #Se o while possui continuação normal,
            #volta para verificar a condição novamente
            if whileTrue is not None:
                self.cfg.terminate(
                    whileTrue,
                    Jump(condBlock.id)
                )

            #retorna None porque não existe continuação normal depois de um while (true).
            return None

        #restoblock foi jogado aqui, de agora em diante a lógica segue o que eraantes
        restoBlock = self.cfg.new_block()

         #Define os dois caminhos possíveis da condição, dando para o condBlock essa checagem
        #verdadeiro para executar o whileBlock e o false, para executar restoBlock
        self.cfg.terminate(
            condBlock.id,
            Branch(
                statement.condition,
                whileBlock.id,
                restoBlock.id
            )
        )

        #Constrói os comandos que estão dentro do while
        whileTrue = self._build_block(
            statement.body,
            whileBlock.id
        )

        #Se o while possui continuação normal,
        #volta para verificar a condição novamente
        if whileTrue is not None:
            self.cfg.terminate(
                whileTrue,
                Jump(condBlock.id)
            )

        #Retorna o bloco em que a execução continua após o while.
        return restoBlock.id
           


        raise NotImplementedError("implemente CFGBuilder._build_while")
