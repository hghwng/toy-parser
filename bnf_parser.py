#!/usr/bin/env python
from enum import Enum
from grammar import Grammar


class _BNFParser:
    '''
    bnf  := prod end | prod bnf
    prod := nterm ':=' rhs
    syms := sym | sym syms
    rhs  := syms | syms '|' rhs
    '''

    class Token(Enum):
        END = 1
        SYM = 2
        KEYWORD = 3

    def __init__(self, buf: str):
        self.pos = 0
        self.tokens = self.tokenize(buf)
        self.grammar = Grammar()
        self.parse_bnf()
        self.fix_grammar()

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (self.Token.END, None)

    def get(self, n=1):
        result = self.peek()
        self.pos += n
        return result

    def unget(self, n=1):
        self.pos -= n

    def fix_grammar(self):
        all_syms = set()
        for prodlist in self.grammar.prods.values():
            for prod in prodlist:
                all_syms.update(prod.syms)
        self.grammar.terms = all_syms - self.grammar.prods.keys() - set('@')

    def parse_rhs(self):
        result = list()
        while True:
            token = self.get()
            if token[0] == self.Token.END:
                self.unget()
                return result
            if token[0] == self.Token.KEYWORD:
                if token[1] == '|':
                    return result
                else:
                    raise SyntaxError("Unexpected token " + str(token))
            result.append(token[1])

    def parse_prod(self):
        token = self.get()
        if token[0] != self.Token.SYM:
            raise SyntaxError("Nonterminal expected, got " + str(token))
        nterm = token[1]
        if not self.grammar.start:
            self.grammar.start = nterm

        token = self.get()
        if token[0] != self.Token.KEYWORD or token[1] != ':=':
            raise SyntaxError("Keyword ':=' expected, got " + str(token))

        while True:
            if self.peek()[0] == self.Token.END:
                return
            prod_list = self.parse_rhs()
            if not len(prod_list):
                raise SyntaxError("Empty right hand side of production "
                                  "for nonterminal " + nterm)
            self.grammar.add_production(nterm, prod_list)

    def parse_bnf(self):
        while True:
            token = self.peek()
            if token[0] == self.Token.END:
                if token[1] is None:
                    return
                else:
                    self.get()
            else:
                self.parse_prod()

    def tokenize(self, buf: str) -> list:
        result = list()
        import re
        regexp_space = re.compile(r"[ \t]+")
        regexps = (
            (self.Token.KEYWORD, re.compile(r"\||:=")),
            (self.Token.SYM, re.compile(r"[^ \t\r\n]+")),
            (self.Token.END, re.compile(r"[\r\n]+")),
        )

        i = 0
        while i < len(buf):
            # Skip spaces
            m = regexp_space.match(buf, i)
            if m:
                i = m.end()
            if i == len(buf):
                break

            for token, regexp in regexps:
                m = regexp.match(buf, i)
                if m:
                    if token == self.Token.SYM:
                        if m.group() == r"'\''":
                            result.append((self.Token.SYM, "'"))
                        else:
                            result.append((token, m.group()))
                    else:
                        result.append((token, m.group()))
                    i = m.end()
                    break
            else:
                raise SyntaxError("Unknown token at pos {} ({})".format(
                    i, buf[i:i + 10]))
        return result


def parse(bnf: str) -> Grammar:
    parser = _BNFParser(bnf)
    return parser.grammar


def main():
    print(parse(_BNFParser.__doc__))


if __name__ == '__main__':
    main()
