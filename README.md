# Projeto MicroC — Etapa 6: pseudoRV64

Implemente geração completa para pseudoRV64. Leia [ENUNCIADO.pdf](ENUNCIADO.pdf), que reúne a exposição, as interfaces e os exemplos desta etapa. Esse é o único PDF desta entrega. A especificação MicroC usada na disciplina continua sendo a já distribuída à turma. A entrega encerra-se no **domingo, 15 de novembro de 2026, às 23h59, no horário de Brasília**. O commit considerado deve estar no repositório correto do grupo no GitHub até esse horário.

## Recupere o frontend

Reúna todos os módulos anteriores diretamente em `previous/`. Copie primeiro os módulos e pacotes que estavam em `previous/` da Semântica 2. Depois copie os módulos e pacotes da raiz da Semântica 2 para essa mesma pasta. Em conflitos, prevalece a versão da raiz da Semântica 2. Preserve os carregadores `load_previous.py` fornecidos nesta etapa. Não copie a pasta `previous/` como subdiretório, Git, ambientes virtuais ou caches. Use o runner da raiz e mantenha os imports anteriores. O carregador prioriza a raiz do starter e a pasta única `previous/`, mantendo classes únicas.

## Material inicial e entrega

A infraestrutura de IR, executor, printer, USE/DEF, contexto, predicados e representação de regras está preenchida. O grupo implementa `codegen.py`, `selector.py` e `catalogue.py`. Pode criar auxiliares.

Traduza comandos ad hoc. Selecione todas as expressões por padrões de árvores com DP. Implemente matching, custos mínimos, reconstrução e ações. Não altere os contratos da AST, símbolos ou IR. Não escreva assembly, alocação, vivacidade ou ABI nesta etapa.

## Executar

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q tests/test_infrastructure.py
python -m pytest -q
python runner.py examples/selecao.mc --dump-ir
python runner.py examples/curto_circuito.mc --run
python runner.py examples/integrado.mc --run
```

O modo padrão mostra IR. `--run` imprime apenas a saída do programa. O retorno integral de main fica disponível em `Interpreter.run(...).main_return`. O status do runner é 0 no sucesso, 1 para erros anteriores, 2 para uso/leitura, 3 para implementação pendente e 4 para IR inválida ou falha de execução. `--max-steps` limita execução.

Os testes de infraestrutura devem passar antes da implementação. Os demais falham enquanto houver partes pendentes. Não use skip ou xfail para esconder essas falhas. A avaliação confere custos, estrutura e comportamento. Não exige dumps idênticos, IDs específicos, SSA ou eliminação de código inalcançável. Testes próprios são recomendados. Não há relatório ou bônus por otimizações extras.

Os testes públicos estão em três módulos: `test_infrastructure.py` verifica as partes fornecidas, `test_codegen.py` apresenta os primeiros casos de geração e seleção, e `test_public_scenarios.py` amplia comparações, controle, efeitos, chamadas, strings e contratos do seletor. Os exemplos usados no enunciado também são verificados. A fonte editável do enunciado fica em `docs/pseudorv64.tex`. Compile o enunciado a partir de `docs/` com `latexmk -pdf -interaction=nonstopmode -halt-on-error pseudorv64.tex`.
