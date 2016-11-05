#!/usr/bin/env python
from grammar import Grammar, Production


def _update_set(dst: set, to_add: set) -> bool:
    old_len = len(dst)
    dst.update(to_add)
    return old_len != len(dst)


class LL1Constructor:
    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.first = dict([(sym, set()) for sym in grammar.prods])
        self.first['@'] = {'@'}
        self._construct_first()

        self.follow = dict([(sym, set()) for sym in grammar.prods])
        self._construct_follow()

        # self.table[nterm][term] = Production
        self.table = dict([(sym, list()) for sym in grammar.prods])
        self._construct_table()

    def __str__(self):
        result = 'LL(1):'
        max_len = max([len(x) for x in self.grammar.prods])

        conflicts = self.get_conflict_entries()
        if conflicts:
            result += ' (NOT an LL(1) grammar)'

        result += '\n  FIRST:'
        for sym in self.grammar.prods:
            result += '\n    {}: {}'.format(
                sym.ljust(max_len), ' '.join(self.first[sym]))

        result += '\n  FOLLOW:'
        for sym in self.grammar.prods:
            result += '\n    {}: {}'.format(
                sym.ljust(max_len), ' '.join(self.follow[sym]))

        result += '\n  Table:'
        for nterm, pairs in self.table.items():
            result += '\n    {}:'.format(nterm)
            for term, prod in sorted(pairs, key=lambda x: x[0]):
                result += '\n      {}: {}'.format(term, prod)

        if conflicts:
            result += '\n  Conflicts:'
            for nterm, term, prods in conflicts:
                result += '\n    {}, {}:'.format(nterm, term)
                for prod in prods:
                    result += '\n      ' + str(prod)

        return result

    def _construct_first(self):
        # FIRST(a) = {a}
        for term in self.grammar.terms:
            self.first[term] = {term}

        changed = True
        while changed:
            changed = False
            for nterm in self.grammar.prods:
                if self._construct_first_nterm(nterm):
                    changed = True

    def _construct_first_nterm(self, nterm: str) -> bool:
        changed = False
        for prod in self.grammar.prods[nterm]:
            for sym in prod.syms:
                if sym != '@' and tuple(self.first[sym]) != ('@',):
                    if _update_set(self.first[nterm], self.first[sym]):
                        changed = True
                    break
            else:
                if _update_set(self.first[nterm], {'@'}):
                    self.first[nterm].add('@')
                    changed = True
        return changed

    def _construct_follow(self):
        self.follow[self.grammar.start] = {'$'}
        changed = True
        while changed:
            changed = False
            for prodlist in self.grammar.prods.values():
                for prod in prodlist:
                    if self._construct_follow_nterm(prod):
                        changed = True

    def _construct_follow_nterm(self, prod: Production) -> bool:
        changed = False
        i = 0
        while i < len(prod.syms):
            nterm = prod.syms[i]
            # Only process nonterminals
            if not self.grammar.is_nonterminal(nterm):
                i += 1
                continue
            i += 1

            remaining_syms = prod.syms[i:]
            remaining_first = self.get_first_from_syms(remaining_syms)
            if _update_set(self.follow[nterm], remaining_first - {'@'}):
                changed = True
            if '@' in remaining_first:
                if _update_set(self.follow[nterm], self.follow[prod.nterm]):
                    changed = True
        return changed

    def _construct_table(self):
        for nterm, prodlist in self.grammar.prods.items():
            for prod in prodlist:
                first = self.get_first_from_syms(prod.syms)
                for term in first:
                    if term == '@':
                        for term in self.follow[nterm]:
                            if term != '@':
                                self.table[nterm].append((term, prod))
                    else:
                        self.table[nterm].append((term, prod))

    # returns {'@'} on empty syms
    def get_first_from_syms(self, syms: list) -> set:
        # First, assume that eps is already in FIRST
        result = {'@'}
        for sym in syms:
            result.update(self.first[sym])
            if '@' not in self.first[sym]:
                # If the eps transition link stops here, remove eps
                return result - {'@'}
        # Eps transition link doesn't stop till end, keep it
        return result

    # result[index] = tuple(nonterm, term, list(Productions))
    def get_conflict_entries(self) -> list:
        result = list()
        for nterm, pairs in self.table.items():
            terms = set([pair[0] for pair in pairs])
            for term in terms:
                prods = list(filter(lambda pair: pair[0] == term, pairs))
                if len(prods) != 1:
                    result.append((nterm, term, [pair[1] for pair in prods]))
        return result


def _demo_construction(bnf):
    from bnf_parser import parse
    grammar = parse(bnf)
    print(grammar)
    constructor = LL1Constructor(grammar)
    print(constructor)


def main():
    bnf = '''
    E  := T E'
    E' := '+' T E' | @
    T  := F T'
    T' := '*' F T' | @
    F  := '(' E ')' | id
    '''
    _demo_construction(bnf)

    bnf = '''
    S  := 'i' E 't' S S' | a
    S' := 'e' S | @
    E  := b
    '''
    _demo_construction(bnf)


if __name__ == '__main__':
    main()
