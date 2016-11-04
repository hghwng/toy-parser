#!/usr/bin/env python
from grammar import Grammar, Production


class _EliminateLeftRecursion:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.nterms = tuple(grammar.prods.keys())

        for elim_idx, elim in enumerate(self.nterms):
            prods = self.grammar.prods[elim]
            prods = self.elim_indirect(elim, elim_idx, prods)
            prods = self.elim_direct(elim, prods)
            self.grammar.prods[elim] = prods

    def elim_direct(self, elim, elim_prods):
        recur_prods = list()
        nonrecur_prods = list()
        for prod in elim_prods:
            if prod.syms[0] == elim:
                recur_prods.append(prod)
            else:
                nonrecur_prods.append(prod)
        if not recur_prods:
            return nonrecur_prods

        new_nterm = self.grammar.get_alt_nonterminal(elim)

        for recur_prod in recur_prods:
            syms = list(recur_prod.syms[1:])
            syms.append(new_nterm)
            self.grammar.add_production(new_nterm, syms)
        self.grammar.add_production(new_nterm, '@')

        new_prods = list()
        for prod in nonrecur_prods:
            syms = list(prod.syms)
            syms.append(new_nterm)
            new_prods.append(Production(elim, syms))
        return new_prods

    def elim_indirect(self, elim, elim_idx, elim_prods):
        new_prods = list()
        replaced = [False] * len(elim_prods)
        for chk in self.nterms[:elim_idx]:
            chk_prods = self.grammar.prods[chk]
            for prod_idx, prod in enumerate(elim_prods):
                if prod.syms[0] == chk:
                    # Replace prod.nterm -> chk other_syms
                    # with prod.nterm -> chk.syms other_syms
                    for chk_prod in chk_prods:
                        new_syms = chk_prod.syms + prod.syms[1:]
                        new_prods.append(Production(elim, new_syms))
                    replaced[prod_idx] = True
        for prod_idx, prod in enumerate(elim_prods):
            if not replaced[prod_idx]:
                new_prods.append(prod)
        return new_prods


def eliminate(grammar: Grammar):
    dup = grammar.duplicate()
    elim = _EliminateLeftRecursion(dup)
    return elim.grammar


def main():
    bnf = '''
    S := X a | b
    X := X c | S d | @
    '''
    from bnf_parser import parse
    grammar = parse(bnf)
    elim_grammar = eliminate(grammar)
    print(grammar)
    print(elim_grammar)


if __name__ == '__main__':
    main()
