#!/usr/bin/env python
from collections import defaultdict


class Grammar:
    def __init__(self):
        self.start = None
        self.terms = set()   # terminals
        # prods[nterm] = list of Production objects
        self.prods = defaultdict(list)

    def add_production(self, nterm, syms):
        production = Production(nterm, syms)
        self.prods[nterm].append(production)

    def is_nonterminal(self, symbol: str) -> bool:
        return symbol in self.prods

    def is_terminal(self, symbol: str) -> bool:
        return symbol in self.terms

    def get_alt_nonterminal(self, nonterm: str) -> str:
        nonterm += "'"
        while nonterm in self.prods:
            nonterm += "'"
        return nonterm

    def get_start_prodctions(self):
        return self.prods[self.start]

    def duplicate(self):
        from copy import deepcopy
        return deepcopy(self)

    def __str__(self):
        result = "Grammar:\n"
        result += "  Start: " + self.start
        result += "\n  Terminals: " + " ".join(self.terms)
        result += "\n  Nonterminals: " + " ".join(self.prods.keys())
        result += "\n  Productions:"
        for prodlist in self.prods.values():
            for prod in prodlist:
                result += "\n    " + str(prod)
        return result


class Production:
    def __init__(self, nterm: str, syms: list):
        self.nterm = nterm
        self.syms = Production.remove_eps(syms)

    def __eq__(self, other):
        return self.nterm == other.nterm and self.syms == other.syms

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        result = hash(self.nterm)
        for sym in self.syms:
            result ^= hash(sym)
        return result

    @staticmethod
    def remove_eps(syms: list) -> list:
        for sym in syms:
            if sym != '@':
                break
        else:
            return ['@']
        return list(filter(lambda x: x != '@', syms))

    def __repr__(self):
        return "Production({}, {})".format(self.nterm, self.syms)

    def __str__(self):
        return "{} → {}".format(self.nterm, " ".join(self.syms))
