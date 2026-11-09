"""Geração de pseudoRV64: comandos ad hoc + expressões por cobertura de custo mínimo."""

import load_previous
import ir as I
from ir import Context, ProgramIR, FunctionIR
from ast_nodes import (
    Assignment,
    Block,
    CallStmt,
    IfStmt,
    PrintStmt,
    ReturnStmt,
    StringLiteral,
    TypeName,
    VarDecl,
    WhileStmt,
)
from catalogue import catalogue
from patterns import REG, COND, EFFECT, signed_literal
from selector import Selector, SelectionError


class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def __init__(self):
        self.selector = Selector(catalogue())
        self.ctx = None
        self.table = None
        self.actions = self._build_actions()

    # ------------------------------------------------------------------
    # Programa e funções
    # ------------------------------------------------------------------
    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        program_ir = ProgramIR()
        self.table = None
        for decl in program.functions:
            symbol = decl.metadata["symbol"]
            function_ir = FunctionIR(symbol)
            program_ir.functions.append(function_ir)
            self.ctx = Context(function_ir, program_ir)

            # Um Param por parâmetro, no início, índices a partir de zero.
            for index, parameter in enumerate(decl.parameters):
                register = self.ctx.variable(parameter.metadata["symbol"])
                self.ctx.emit(I.Param(register, index, origin=parameter.span))

            self.statement(decl.body)

            # Fim normal de função void também é um Return(None).
            if symbol.type is TypeName.VOID:
                self.ctx.emit(I.Return(None, origin=decl.body.span))
        self.ctx = None
        return program_ir

    # ------------------------------------------------------------------
    # Comandos (tradução ad hoc)
    # ------------------------------------------------------------------
    def statement(self, node):
        """Traduza um comando ad hoc."""
        ctx = self.ctx

        if isinstance(node, Block):
            for inner in node.statements:
                self.statement(inner)

        elif isinstance(node, VarDecl):
            register = ctx.variable(node.metadata["symbol"])
            # Sem inicializador: nada é emitido (não há zero implícito).
            if node.initializer is not None:
                value = self.expression(node.initializer, REG)
                ctx.emit(I.Move(register, value, origin=node.span))

        elif isinstance(node, Assignment):
            # Avalia o valor antes de escrever no VReg do símbolo.
            value = self.expression(node.value, REG)
            register = ctx.variable(node.target.metadata["symbol"])
            ctx.emit(I.Move(register, value, origin=node.span))

        elif isinstance(node, CallStmt):
            self.expression(node.call, EFFECT)

        elif isinstance(node, IfStmt):
            then_label = ctx.label()
            end_label = ctx.label()
            else_label = ctx.label() if node.else_block is not None else end_label
            self.expression(node.condition, COND, then_label, else_label)
            ctx.emit(I.LabelInstr(then_label))
            self.statement(node.then_block)
            if node.else_block is not None:
                ctx.emit(I.Jump(end_label, origin=node.span))
                ctx.emit(I.LabelInstr(else_label))
                self.statement(node.else_block)
            ctx.emit(I.LabelInstr(end_label))

        elif isinstance(node, WhileStmt):
            head = ctx.label()
            body = ctx.label()
            exit_label = ctx.label()
            ctx.emit(I.LabelInstr(head))
            self.expression(node.condition, COND, body, exit_label)
            ctx.emit(I.LabelInstr(body))
            self.statement(node.body)
            ctx.emit(I.Jump(head, origin=node.span))
            ctx.emit(I.LabelInstr(exit_label))

        elif isinstance(node, ReturnStmt):
            if node.value is None:
                ctx.emit(I.Return(None, origin=node.span))
            else:
                value = self.expression(node.value, REG)
                ctx.emit(I.Return(value, origin=node.span))

        elif isinstance(node, PrintStmt):
            # Cada item é impresso por completo antes do próximo.
            for item in node.items:
                if isinstance(item, StringLiteral):
                    ctx.emit(I.PrintString(ctx.string(item.value), origin=item.span))
                else:
                    value = self.expression(item, REG)
                    if item.metadata.get("type") is TypeName.BOOL:
                        ctx.emit(I.PrintBool(value, origin=item.span))
                    else:
                        ctx.emit(I.PrintInt(value, origin=item.span))
            ctx.emit(I.PrintString(ctx.string("\n"), origin=node.span))

        else:
            raise NotImplementedError(f"comando não suportado: {type(node).__name__}")

    # ------------------------------------------------------------------
    # Expressões: análise (DP) + reconstrução da cobertura escolhida
    # ------------------------------------------------------------------
    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito.

        REG devolve o VReg do valor; COND emite controle para os labels;
        EFFECT emite a chamada descartando o resultado.
        """
        saved = self.table
        self.table = self.selector.analyze(node)
        try:
            return self._cover(node, result_class, true_label, false_label)
        finally:
            self.table = saved

    def _cover(self, node, result_class, true_label=None, false_label=None):
        choice = self.table.lookup(node, result_class)
        if choice is None:
            span = node.span
            raise SelectionError(
                f"expressão sem cobertura para {result_class.value} "
                f"na posição {span.start_line}:{span.start_column}"
            )
        action = self.actions.get(choice.rule.action)
        if action is None:
            raise NotImplementedError(f"ação sem implementação: {choice.rule.action}")
        return action(node, choice, true_label, false_label)

    def _sub(self, choice, index, true_label=None, false_label=None):
        child, result_class = choice.subproblems[index]
        return self._cover(child, result_class, true_label, false_label)

    # ------------------------------------------------------------------
    # Ações emissoras
    # ------------------------------------------------------------------
    def _build_actions(self):
        actions = {
            "literal_reg": self._literal_reg,
            "identifier_reg": self._identifier_reg,
            "literal_imm12": lambda n, c, t, f: signed_literal(n),
            "literal_pow2": lambda n, c, t, f: signed_literal(n).bit_length() - 1,
            "negate_reg": self._negate_reg,
            "add_imm_right": self._add_imm_right,
            "add_imm_left": self._add_imm_left,
            "sub_imm": self._sub_imm,
            "mul_pow2_right": self._mul_pow2_right,
            "mul_pow2_left": self._mul_pow2_left,
            "not_reg": self._not_reg,
            "not_cond": self._not_cond,
            "and_cond": self._and_cond,
            "or_cond": self._or_cond,
            "and_reg": self._logic_reg(is_and=True),
            "or_reg": self._logic_reg(is_and=False),
            "bool_cond": self._bool_cond,
            "identifier_cond": self._identifier_cond,
            "call_reg": self._call_reg,
            "call_effect": self._call_effect,
            "call_cond": self._call_cond,
            "less_reg": self._slt_reg(swap=False, negate=False),
            "greater_reg": self._slt_reg(swap=True, negate=False),
            "less_equal_reg": self._slt_reg(swap=True, negate=True),
            "greater_equal_reg": self._slt_reg(swap=False, negate=True),
            "equal_reg": self._xor_reg(I.Seqz),
            "not_equal_reg": self._xor_reg(I.Snez),
            # (instrução, trocar operandos?)
            "less_cond": self._branch_cond(I.Blt, False),
            "greater_cond": self._branch_cond(I.Blt, True),
            "less_equal_cond": self._branch_cond(I.Bge, True),
            "greater_equal_cond": self._branch_cond(I.Bge, False),
            "equal_cond": self._branch_cond(I.Beq, False),
            "not_equal_cond": self._branch_cond(I.Bne, False),
        }
        for name, instruction in [
            ("add_reg", I.Add),
            ("sub_reg", I.Sub),
            ("mul_reg", I.Mul),
            ("div_reg", I.Div),
            ("rem_reg", I.Rem),
        ]:
            actions[name] = self._arith(instruction)
        return actions

    # --- folhas -------------------------------------------------------
    def _literal_reg(self, node, choice, t, f):
        value = getattr(node, "value", None)
        if isinstance(value, bool):  # BoolLiteral: materializa 0/1
            value = int(value)
        else:  # IntLiteral ou negação imediata de IntLiteral
            value = signed_literal(node)
        dst = self.ctx.temp()
        self.ctx.emit(I.Li(dst, value, origin=node.span))
        return dst

    def _identifier_reg(self, node, choice, t, f):
        return self.ctx.variable(node.metadata["symbol"])

    # --- aritmética ---------------------------------------------------
    def _negate_reg(self, node, choice, t, f):
        src = self._sub(choice, 0)
        dst = self.ctx.temp()
        self.ctx.emit(I.Neg(dst, src, origin=node.span))
        return dst

    def _arith(self, instruction):
        def action(node, choice, t, f):
            lhs = self._sub(choice, 0)  # esquerda antes da direita
            rhs = self._sub(choice, 1)
            dst = self.ctx.temp()
            self.ctx.emit(instruction(dst, lhs, rhs, origin=node.span))
            return dst

        return action

    def _add_imm_right(self, node, choice, t, f):
        src = self._sub(choice, 0)
        imm = self._sub(choice, 1)
        dst = self.ctx.temp()
        self.ctx.emit(I.Addi(dst, src, imm, origin=node.span))
        return dst

    def _add_imm_left(self, node, choice, t, f):
        imm = self._sub(choice, 0)
        src = self._sub(choice, 1)
        dst = self.ctx.temp()
        self.ctx.emit(I.Addi(dst, src, imm, origin=node.span))
        return dst

    def _sub_imm(self, node, choice, t, f):
        src = self._sub(choice, 0)  # x é avaliado uma única vez
        imm = -signed_literal(node.right)
        dst = self.ctx.temp()
        self.ctx.emit(I.Addi(dst, src, imm, origin=node.span))
        return dst

    def _mul_pow2_right(self, node, choice, t, f):
        src = self._sub(choice, 0)
        shift = self._sub(choice, 1)
        dst = self.ctx.temp()
        self.ctx.emit(I.Slli(dst, src, shift, origin=node.span))
        return dst

    def _mul_pow2_left(self, node, choice, t, f):
        shift = self._sub(choice, 0)
        src = self._sub(choice, 1)
        dst = self.ctx.temp()
        self.ctx.emit(I.Slli(dst, src, shift, origin=node.span))
        return dst

    # --- comparações como valor --------------------------------------
    def _slt_reg(self, swap, negate):
        def action(node, choice, t, f):
            lhs = self._sub(choice, 0)
            rhs = self._sub(choice, 1)
            if swap:
                lhs, rhs = rhs, lhs
            dst = self.ctx.temp()
            self.ctx.emit(I.Slt(dst, lhs, rhs, origin=node.span))
            if negate:  # a <= b  ==  !(b < a);  a >= b  ==  !(a < b)
                final = self.ctx.temp()
                self.ctx.emit(I.Seqz(final, dst, origin=node.span))
                return final
            return dst

        return action

    def _xor_reg(self, test):
        def action(node, choice, t, f):
            lhs = self._sub(choice, 0)
            rhs = self._sub(choice, 1)
            diff = self.ctx.temp()
            self.ctx.emit(I.Xor(diff, lhs, rhs, origin=node.span))
            dst = self.ctx.temp()
            self.ctx.emit(test(dst, diff, origin=node.span))
            return dst

        return action

    # --- comparações como controle -----------------------------------
    def _branch_cond(self, branch, swap):
        def action(node, choice, true_label, false_label):
            lhs = self._sub(choice, 0)
            rhs = self._sub(choice, 1)
            if swap:  # a > b  ==  b < a;  a <= b  ==  b >= a
                lhs, rhs = rhs, lhs
            self.ctx.emit(branch(lhs, rhs, true_label, origin=node.span))
            self.ctx.emit(I.Jump(false_label, origin=node.span))

        return action

    # --- lógicos ------------------------------------------------------
    def _not_reg(self, node, choice, t, f):
        src = self._sub(choice, 0)
        dst = self.ctx.temp()
        self.ctx.emit(I.Seqz(dst, src, origin=node.span))
        return dst

    def _not_cond(self, node, choice, true_label, false_label):
        self._sub(choice, 0, false_label, true_label)  # inverte destinos

    def _and_cond(self, node, choice, true_label, false_label):
        middle = self.ctx.label()
        self._sub(choice, 0, middle, false_label)
        self.ctx.emit(I.LabelInstr(middle))  # 2º filho só se o 1º foi verdadeiro
        self._sub(choice, 1, true_label, false_label)

    def _or_cond(self, node, choice, true_label, false_label):
        middle = self.ctx.label()
        self._sub(choice, 0, true_label, middle)
        self.ctx.emit(I.LabelInstr(middle))  # 2º filho só se o 1º foi falso
        self._sub(choice, 1, true_label, false_label)

    def _logic_reg(self, is_and):
        def action(node, choice, t, f):
            dst = self.ctx.temp()
            true_label, false_label = self.ctx.label(), self.ctx.label()
            join = self.ctx.label()
            middle = self.ctx.label()
            if is_and:
                self._sub(choice, 0, middle, false_label)
            else:
                self._sub(choice, 0, true_label, middle)
            self.ctx.emit(I.LabelInstr(middle))
            self._sub(choice, 1, true_label, false_label)
            self.ctx.emit(I.LabelInstr(true_label))
            self.ctx.emit(I.Li(dst, 1, origin=node.span))
            self.ctx.emit(I.Jump(join, origin=node.span))
            self.ctx.emit(I.LabelInstr(false_label))
            self.ctx.emit(I.Li(dst, 0, origin=node.span))
            self.ctx.emit(I.LabelInstr(join))
            return dst

        return action

    def _bool_cond(self, node, choice, true_label, false_label):
        target = true_label if node.value else false_label
        self.ctx.emit(I.Jump(target, origin=node.span))

    def _identifier_cond(self, node, choice, true_label, false_label):
        register = self.ctx.variable(node.metadata["symbol"])
        self.ctx.emit(I.Bnez(register, true_label, origin=node.span))
        self.ctx.emit(I.Jump(false_label, origin=node.span))

    # --- chamadas -----------------------------------------------------
    def _arguments(self, choice):
        # Esquerda para a direita; cada argumento é completado antes do próximo.
        return tuple(self._sub(choice, i) for i in range(len(choice.subproblems)))

    def _call_reg(self, node, choice, t, f):
        args = self._arguments(choice)
        dst = self.ctx.temp()
        self.ctx.emit(I.Call(dst, node.metadata["symbol"], args, origin=node.span))
        return dst

    def _call_effect(self, node, choice, t, f):
        args = self._arguments(choice)
        self.ctx.emit(I.Call(None, node.metadata["symbol"], args, origin=node.span))

    def _call_cond(self, node, choice, true_label, false_label):
        args = self._arguments(choice)
        dst = self.ctx.temp()
        self.ctx.emit(I.Call(dst, node.metadata["symbol"], args, origin=node.span))
        self.ctx.emit(I.Bnez(dst, true_label, origin=node.span))
        self.ctx.emit(I.Jump(false_label, origin=node.span))