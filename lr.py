#!/usr/bin/env python
from collections import defaultdict
from grammar import Grammar, Production
import bnf_parser
import ll1

class LR0Item:
    def __init__(self, prod: Production=None, pos=0):
        self.prod = prod
        self.pos = pos

    def __eq__(self, other):
        return self.prod == other.prod and self.pos == other.pos

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(self.prod) ^ hash(self.pos)

    def get_syms_after_dot(self):
        if self.pos >= len(self.prod.syms):
            return tuple()
        result = tuple(self.prod.syms[self.pos:])
        if result == ('@',):
            return tuple()
        return result

    def get_next_item(self):
        return LR0Item(self.prod, self.pos + 1)

    def __repr__(self):
        return "LR0Item({}, {})".format(self.prod, self.pos)

    def __str__(self):
        dot_syms = list(self.prod.syms)
        dot_syms.insert(self.pos, '·')
        return "{} → {}".format(self.prod.nterm, " ".join(dot_syms))


class LR1Item(LR0Item):
    def __init__(self, prod: Production=None, pos=0, lookahead=frozenset()):
        LR0Item.__init__(self, prod, pos)
        self.lookahead = lookahead

    def __eq__(self, other):
        return LR0Item.__eq__(self, other) and self.lookahead == other.lookahead

    def __hash__(self):
        return LR0Item.__hash__(self) ^ hash(self.lookahead)

    def __repr__(self):
        return "LR1Item({}, {} {})".format(self.prod, self.pos, self.lookahead)

    def __str__(self):
        return "[{}, {}]".format(LR0Item.__str__(self), '/'.join(self.lookahead))

    def get_next_item(self):
        return LR1Item(self.prod, self.pos + 1, self.lookahead)

class LR0AlgorithmSuit:
    NAME = 'LR0'

    def build_item(self, prod: Production, parent: LR0Item=None):
        self = self
        parent = parent
        return LR0Item(prod)

    def construct_table(self, transitions: list) -> list:
        # table[state] = dict(symbol -> action)
        for src_state, transitions in enumerate(transitions):
            for sym, dst_state in transitions.items():
                pass


class LR1AlgorithmSuit:
    NAME = 'LR1'

    def __init__(self, grammar: Grammar):
        self.first = ll1.construct_first(grammar)

    def build_item(self, prod: Production, parent: LR1Item=None):
        if not parent:
            return LR1Item(prod, 0, frozenset({'$'}))

        lookaheads = ll1.get_first_from_syms(self.first, parent.get_syms_after_dot()[1:])
        if '@' in lookaheads:
            lookaheads.discard('@')
            lookaheads.update(parent.lookahead)
        result = LR1Item(prod, 0, frozenset(lookaheads))
        return result


def get_closure(grammar: Grammar, item, algo_suit) -> set:
    new_items = None
    if hasattr(item, '__iter__'):
        new_items = set(item)
    else:
        new_items = {item}

    result = set()
    while new_items:
        item = new_items.pop()
        result.add(item)

        next_syms = item.get_syms_after_dot()
        if not next_syms or \
            not grammar.is_nonterminal(next_syms[0]):
            continue
        for prod in grammar.prods[next_syms[0]]:
            new_item = algo_suit.build_item(prod, item)
            if new_item not in result:
                new_items.add(new_item)
    return result


def construct_argumented_grammar(grammar: Grammar) -> Grammar:
    START_NTERM = '!S'
    g = grammar.duplicate()
    g.add_production(START_NTERM, (g.start,))
    g.start = START_NTERM
    return g


def categorize_items_by_next_symbol(closures: set) -> dict:
    # result[sym] = set(item)
    result = defaultdict(set)
    for item in closures:
        next_syms = item.get_syms_after_dot()
        if next_syms:
            result[next_syms[0]].add(item)
        else:
            result[''].add(item)
    return dict(result)


def construct_kernels_closures_transitions(grammar: Grammar, algo_suit):
    closures = list()      # closures[state] = set(item)
    transitions = list()   # transitions[src_state][sym] = dst_state
    kernels = list()       # kernels[state] = set(kernel_item)
    kernels.append(frozenset({algo_suit.build_item(grammar.prods[grammar.start][0])}))

    kernel_idx = 0
    while kernel_idx < len(kernels):
        src_items_closure = get_closure(grammar, kernels[kernel_idx], algo_suit)
        closures.append(frozenset(src_items_closure))

        next_items = categorize_items_by_next_symbol(src_items_closure)
        transition = dict()
        for next_sym, src_items in next_items.items():
            if not next_sym:
                continue
            next_kernel = frozenset([i.get_next_item() for i in src_items])
            if next_kernel not in kernels:
                kernels.append(next_kernel)
            transition[next_sym] = kernels.index(next_kernel)
        transitions.append(transition)
        kernel_idx += 1
    return kernels, closures, transitions


def dump_dfa(kernels: list, closures: list, transitions: list, export_file):
    export_file.write('digraph {\n  rankdir = "LR";')

    for i, kernel in enumerate(kernels):
        export_file.write('  "node{}" [\n'.format(i))
        export_file.write('    shape = "record"\n')
        export_file.write(r'    label = "I{}\n|'.format(i))
        export_file.write(r'\l'.join([str(t) for t in kernel]))
        nonkernel = closures[i] - kernel
        export_file.write(r'\l')
        if nonkernel:
            export_file.write('|')
            export_file.write(r'\l'.join([str(t) for t in nonkernel]))
            export_file.write(r'\l')
        export_file.write('"\n  ];\n')
    export_file.write('\n\n')
    for src_state, transitions in enumerate(transitions):
        for sym, dst_state in transitions.items():
            line = '  "node{}" -> "node{}" [label="{}"]\n'.format(
                src_state, dst_state, sym)
            export_file.write(line)

    export_file.write('}')


def str_kernels(kernels: list, closures: list) -> str:
    result = '  States:'
    for i, kernel in enumerate(kernels):
        result += '\n    {}:'.format(i)
        for item in kernel:
            result += '\n      {}'.format(item)
        nonkernel = closures[i] - kernel
        if nonkernel:
            result += '\n      (Nonkernel)'
            for item in nonkernel:
                result += '\n      {}'.format(item)
    return result


def str_transitions(transitions: list) -> str:
    result = '  Transitions:'
    for src_state, transitions in enumerate(transitions):
        for sym, dst_state in transitions.items():
            result += '\n    {} {} {}'.format(src_state, sym, dst_state)
    return result


def str_lr(grammar: Grammar, algo_suit_class):
    argumented_grammar = construct_argumented_grammar(grammar)
    algo_suit = algo_suit_class(argumented_grammar)
    kernels, closures, transitions \
        = construct_kernels_closures_transitions(argumented_grammar, algo_suit)
    result = algo_suit.NAME + ':'
    result += '\n' + str_kernels(kernels, closures)
    result += '\n' + str_transitions(transitions)
    return result


def dump_lr(grammar: Grammar, algo_suit_class, export_file):
    argumented_grammar = construct_argumented_grammar(grammar)
    algo_suit = algo_suit_class(argumented_grammar)
    kernels, closures, transitions \
        = construct_kernels_closures_transitions(argumented_grammar, algo_suit)
    dump_dfa(kernels, closures, transitions, export_file)


def main():
    bnf = '''
    S := C C
    C := c C | d
    '''
    grammar = bnf_parser.parse(bnf)
    print(str_lr(grammar, LR1AlgorithmSuit))


if __name__ == '__main__':
    main()
