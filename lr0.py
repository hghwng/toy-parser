#!/usr/bin/env python
from grammar import Grammar, Production
import bnf_parser

_START_NTERM = '!S'

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

    def get_advanced_item(self, n=1):
        return LR0Item(self.prod, self.pos + n)

    def __repr__(self):
        return "LR0Item({}, {})".format(self.prod, self.pos)

    def __str__(self):
        dot_syms = list(self.prod.syms)
        dot_syms.insert(self.pos, '·')
        return "{} → {}".format(self.prod.nterm, " ".join(dot_syms))


def get_closure(grammar: Grammar, item) -> set:
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
            new_item = LR0Item(prod)
            if new_item not in result:
                new_items.add(new_item)
    return result


def construct_argumented_grammar(grammar: Grammar) -> Grammar:
    g = grammar.duplicate()
    g.add_production(_START_NTERM, (g.start,))
    g.start = _START_NTERM
    return g


def construct_kernels_closures_transitions(grammar: Grammar):
    closures = list()      # closures[state] = set(item)
    transitions = list()   # transitions[src_state][sym] = dst_state
    kernels = list()       # kernels[state] = set(kernel_item)
    kernels.append(frozenset({LR0Item(grammar.prods[grammar.start][0])}))

    kernel_idx = 0
    while kernel_idx < len(kernels):
        src_items = kernels[kernel_idx]
        closure_items_set = get_closure(grammar, src_items)
        closures.append(frozenset(closure_items_set))
        closure_items = list(closure_items_set)

        transition = dict()
        for i, item in enumerate(closure_items):
            # Pick the next symbol to process
            next_syms = item.get_syms_after_dot()
            if not next_syms:
                continue
            next_sym = next_syms[0]
            if next_sym in transitions:
                continue

            # Get all items whose next symbol is also next_sym
            dst_items = set()
            for item in closure_items[i:]:
                next_syms = item.get_syms_after_dot()
                if not next_syms or next_syms[0] != next_sym:
                    continue
                dst_items.add(item.get_advanced_item())
            dst_items_frozen = frozenset(dst_items)

            # Store the item set if not exist
            if dst_items not in kernels:
                kernels.append(dst_items_frozen)
            transition[next_sym] = kernels.index(dst_items_frozen)
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


def str_lr0(grammar: Grammar):
    argumented_grammar = construct_argumented_grammar(grammar)
    kernels, closures, transitions = \
        construct_kernels_closures_transitions(argumented_grammar)
    result = 'LR(0):'
    result += '\n' + str_kernels(kernels, closures)
    result += '\n' + str_transitions(transitions)
    return result


def main():
    bnf = '''
    S := ( S R | a
    R := , S R | )
    '''
    grammar = bnf_parser.parse(bnf)
    print(str_lr0(grammar))

if __name__ == '__main__':
    main()
