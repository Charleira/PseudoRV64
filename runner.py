"""Execute o frontend e gere, inspecione ou teste a pseudoRV64."""

# O carregador deve preceder os imports dos módulos do frontend.
import load_previous
import argparse
from pathlib import Path
from Lexer import Lexer, LexerError
from parser import Parser, ParserError
from semantic import SemanticAnalyzer
from semantic_errors import SemanticError
from codegen import CodeGenerator
from executor import Interpreter, validate
from ir import format_ir


def main():
    p = argparse.ArgumentParser(description="Gere e execute pseudoRV64.")
    p.add_argument("source", type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--dump-ir", action="store_true")
    p.add_argument("--max-steps", type=int, default=100000)
    args = p.parse_args()
    try:
        program = Parser(Lexer(args.source.read_text()).scan()).parse()
        # Nenhuma geração ocorre se o frontend rejeitar o programa.
        SemanticAnalyzer().analyze(program)
        ir = CodeGenerator().generate(program)
        validate(ir)
        if args.run:
            print(Interpreter().run(ir, args.max_steps).stdout, end="")
        else:
            print(format_ir(ir))
    except (LexerError, ParserError, SemanticError) as e:
        p.exit(1, str(e) + "\n")
    except (OSError, UnicodeError) as e:
        p.exit(2, str(e) + "\n")
    except NotImplementedError as e:
        p.exit(3, str(e) + "\n")
    except (ValueError, RuntimeError) as e:
        p.exit(4, str(e) + "\n")


if __name__ == "__main__":
    main()
