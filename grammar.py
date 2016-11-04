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
        self.syms = syms

    def __repr__(self):
        return "Production({}, {})".format(self.nterm, self.syms)

    def __str__(self):
        return "{} -> {}".format(self.nterm, " ".join(self.syms))
