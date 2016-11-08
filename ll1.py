#!/usr/bin/env python
from grammar import Grammar, Production


def _update_set(dst: set, to_add: set) -> bool:
    old_len = len(dst)
    dst.update(to_add)
    return old_len != len(dst)


def construct_first(grammar: Grammar) -> list:
    def construct_first_nterm(nterm: str) -> bool:
        changed = False
        for prod in grammar.prods[nterm]:
            for sym in prod.syms:
                if sym != '@' and tuple(first[sym]) != ('@',):
                    if _update_set(first[nterm], first[sym]):
                        changed = True
                    break
            else:
                if _update_set(first[nterm], {'@'}):
                    first[nterm].add('@')
                    changed = True
        return changed

    first = dict([(sym, set()) for sym in grammar.prods])
    first['@'] = {'@'}
    # FIRST(a) = {a}
    for term in grammar.terms:
        first[term] = {term}

    changed = True
    while changed:
        changed = False
        for nterm in grammar.prods:
            if construct_first_nterm(nterm):
                changed = True
    return first


# returns {'@'} on empty syms
def get_first_from_syms(first: list, syms: list) -> set:
    # First, assume that eps is already in FIRST
    result = {'@'}
    for sym in syms:
        result.update(first[sym])
        if '@' not in first[sym]:
            # If the eps transition link stops here, remove eps
            return result - {'@'}
    # Eps transition link doesn't stop till end, keep it
    return result


def construct_follow(grammar: Grammar, first: list) -> list:
    def construct_follow_nterm(prod: Production) -> bool:
        changed = False
        i = 0
        while i < len(prod.syms):
            nterm = prod.syms[i]
            # Only process nonterminals
            if not grammar.is_nonterminal(nterm):
                i += 1
                continue
            i += 1

            remaining_syms = prod.syms[i:]
            remaining_first = get_first_from_syms(first, remaining_syms)
            if _update_set(follow[nterm], remaining_first - {'@'}):
                changed = True
            if '@' in remaining_first:
                if _update_set(follow[nterm], follow[prod.nterm]):
                    changed = True
        return changed

    follow = dict([(sym, set()) for sym in grammar.prods])
    follow[grammar.start] = {'$'}
    changed = True
    while changed:
        changed = False
        for prodlist in grammar.prods.values():
            for prod in prodlist:
                if construct_follow_nterm(prod):
                    changed = True
    return follow


def construct_table(grammar: Grammar, first: list, follow: list) -> dict:
    # table[nterm][term] = Production
    table = dict([(sym, list()) for sym in grammar.prods])
    for nterm, prodlist in grammar.prods.items():
        for prod in prodlist:
            first_set = get_first_from_syms(first, prod.syms)
            for term in first_set:
                if term == '@':
                    for term in follow[nterm]:
                        if term != '@':
                            table[nterm].append((term, prod))
                else:
                    table[nterm].append((term, prod))
    return table


def construct_conflicts(table: dict) -> list:
    # result[index] = tuple(nonterm, term, list(Productions))
    result = list()
    for nterm, pairs in table.items():
        terms = set([pair[0] for pair in pairs])
        for term in terms:
            prods = list(filter(lambda pair, term=term: pair[0] == term, pairs))
            if len(prods) != 1:
                result.append((nterm, term, [pair[1] for pair in prods]))
    return result


def _str_first_or_follow(grammar: Grammar, first: list, title) -> str:
    result = '  ' + title
    for sym in grammar.prods:
        result += '\n    {}: {}'.format(sym, ' '.join(first[sym]))
    return result


def str_follow(grammar: Grammar, follow: list) -> str:
    return _str_first_or_follow(grammar, follow, 'FOLLOW')


def str_first(grammar: Grammar, first: list) -> str:
    return _str_first_or_follow(grammar, first, 'FIRST')


def str_table(table: dict) -> str:
    result = '  Table:'
    for nterm, pairs in table.items():
        result += '\n    {}:'.format(nterm)
        for term, prod in sorted(pairs, key=lambda x: x[0]):
            result += '\n      {}: {}'.format(term, prod)
    return result


def str_conflicts(conflicts: list) -> str:
    result = ''
    for nterm, term, prods in conflicts:
        result += '\n    {}, {}:'.format(nterm, term)
        for prod in prods:
            result += '\n      ' + str(prod)
    if result:
        return '  Conflicts:' + result
    else:
        return '  Conflicts: None'


def str_ll1(grammar: Grammar) -> str:
    first = construct_first(grammar)
    follow = construct_follow(grammar, first)
    table = construct_table(grammar, first, follow)
    conflicts = construct_conflicts(table)

    result = 'LL(1):'
    result += '\n' + str_first(grammar, first)
    result += '\n' + str_follow(grammar, follow)
    result += '\n' + str_table(table)
    result += '\n' + str_conflicts(conflicts)
    return result


def _demo_construction(bnf):
    from bnf_parser import parse
    grammar = parse(bnf)
    print(grammar)
    print(str_ll1(grammar))


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
