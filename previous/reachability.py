"""Alcance no CFG. O percurso da AST já foi realizado pelo builder."""

from __future__ import annotations

from cfg import BlockId, CFG


def compute_reachable(cfg: CFG) -> set[BlockId]:
    """Devolva os IDs alcançáveis a partir da entrada, incluindo a entrada."""
    #aqui atinge os que já atngimos, ou já reachamos para soar como se escreve
    reachable: set[BlockId] = set()
    pending = [cfg.entry]
    while pending:
        current = pending.pop()
        #se o bloco já tá na lista de reachble isso sai do while
        if current in reachable:
            continue
        #adiciona o reachble na lista
        reachable.add(current)
        #percorre todos os blocos sucessores
        for successor in cfg.blocks[current].successors:
            #adicona os sucessores a lista de blocos pendentes que precisamos correr
            pending.append(successor)

    return reachable
    raise NotImplementedError("implemente compute_reachable")
