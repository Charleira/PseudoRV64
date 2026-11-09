"""Reconhecimento de padrões de árvores e custos mínimos por nó e classe (DP)."""

from patterns import (
    Args,
    Choice,
    Need,
    Pattern,
    SelectionTable,
    children,
)

_MISSING = object()


class SelectionError(RuntimeError, ValueError):
    """Raiz (ou subárvore exigida) sem cobertura no catálogo."""


class Selector:
    """Selecione coberturas sem executar expressões ou emitir instruções."""

    def __init__(self, rules):
        self.rules = tuple(rules)

    # ------------------------------------------------------------------
    def analyze(self, expr):
        """Calcule mínimos por nó/classe sem emitir instruções."""
        table = SelectionTable()
        self._visit(expr, table)
        return table

    # ------------------------------------------------------------------
    def _visit(self, node, table):
        # Pós-ordem: todos os filhos (e descendentes) antes do nó.
        for child in children(node):
            self._visit(child, table)

        best = {}  # classe -> Choice mínimo; empates mantêm a primeira regra
        for rule in self.rules:
            subproblems = self._match(rule.pattern, node)
            if subproblems is None:
                continue
            total = rule.cost  # custo próprio + custo total de cada Need
            for child, result_class in subproblems:
                found = table.lookup(child, result_class)
                if found is None:  # alternativa impossível
                    break
                total += found.cost
            else:
                current = best.get(rule.result)
                if current is None or total < current.cost:
                    best[rule.result] = Choice(total, rule, tuple(subproblems))

        for result_class, choice in best.items():
            table.put(node, result_class, choice)

    # ------------------------------------------------------------------
    def _match(self, pattern, node):
        """Casa o padrão com o nó. Devolve a lista de (nó, classe) dos pontos
        Need na ordem do padrão, ou None se não houver correspondência."""
        if pattern.kind is not None and not isinstance(node, pattern.kind):
            return None
        if pattern.operator is not None and (
            getattr(node, "operator", _MISSING) != pattern.operator
        ):
            return None
        if pattern.predicate is not None and not pattern.predicate(node):
            return None

        wanted = pattern.children
        # Predicado sem filhos reconhece a subárvore inteira.
        if not wanted and pattern.predicate is not None:
            return []

        kids = children(node)

        # Args(classe): cada argumento exige a classe, inclusive lista vazia.
        if len(wanted) == 1 and isinstance(wanted[0], Args):
            return [(kid, wanted[0].result) for kid in kids]

        if len(wanted) != len(kids):
            return None

        subproblems = []
        for sub, kid in zip(wanted, kids):
            if isinstance(sub, Need):
                subproblems.append((kid, sub.result))
            elif isinstance(sub, Pattern):
                inner = self._match(sub, kid)
                if inner is None:
                    return None
                subproblems.extend(inner)
            else:
                raise TypeError(f"elemento de padrão inválido: {sub!r}")
        return subproblems