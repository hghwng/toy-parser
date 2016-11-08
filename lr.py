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

    def get_next_syms(self):
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
        return "LR1Item{}".format(str(self))

    def __str__(self):
        return "[{}, {}]".format(LR0Item.__str__(self), '/'.join(self.lookahead))

    def get_next_item(self):
        return LR1Item(self.prod, self.pos + 1, self.lookahead)


class LREdge:
    def __init__(self, src_items, dst_state: int):
        self.src_items = src_items
        self.dst_state = dst_state

    def __repr__(self):
        return "LREdge({}, {})".format(set(self.src_items), self.dst_state)


class LRState:
    def __init__(self, kernel, edges=None):
        self.edges = edges
        self.kernel = kernel

    def __repr__(self):
        return "LRState({}, {})".format(set(self.kernel), self.edges)

    def get_closure(self):
        closure = set()
        for edge in self.edges.values():
            closure.update(edge.src_items)
        return closure

    @staticmethod
    def find_kernel_index(states, kernel):
        kernels = [i.kernel for i in states]
        try:
            return kernels.index(kernel)
        except ValueError:
            return -1


class LR0AlgorithmSuit:
    NAME = 'LR0'

    def __init__(self, grammar: Grammar):
        pass

    def build_item(self, prod: Production, parent: LR0Item=None):
        self = self
        parent = parent
        return LR0Item(prod)


class LR1AlgorithmSuit:
    NAME = 'LR1'

    def __init__(self, grammar: Grammar):
        self.first = ll1.construct_first(grammar)

    def build_item(self, prod: Production, parent: LR1Item=None):
        if not parent:
            return LR1Item(prod, 0, frozenset({'$'}))

        lookaheads = ll1.get_first_from_syms(self.first, parent.get_next_syms()[1:])
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

        next_syms = item.get_next_syms()
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


def _construct_state_transition_dict(grammar: Grammar, src_state: LRState, algo_suit):
    src_closure_items = get_closure(grammar, src_state.kernel, algo_suit)

    src_dict = defaultdict(set)  # edge_src_state[sym] = set(src_items)
    dst_dict = defaultdict(set)  # edge_dst_state[sym] = set(dst_items)
    for item in src_closure_items:
        next_syms = item.get_next_syms()
        if next_syms:
            src_dict[next_syms[0]].add(item)
            dst_dict[next_syms[0]].add(item.get_next_item())
        else:
            src_dict[''].add(item)
    return src_dict, dst_dict


def _construct_edge(states: list, src_dict: dict, dst_dict: dict):
    edges = dict()
    for sym in dst_dict:
        src_items = frozenset(src_dict[sym])
        dst_items = frozenset(dst_dict[sym])
        dst_index = LRState.find_kernel_index(states, dst_items)
        if dst_index == -1:
            dst_index = len(states)
            states.append(LRState(dst_items))
        edges[sym] = LREdge(src_items, dst_index)
    if '' in src_dict:
        edges[''] = LREdge(frozenset(src_dict['']), -1)
    return edges


def construct_states(grammar: Grammar, algo_suit_class):
    grammar = construct_argumented_grammar(grammar)
    algo_suit = algo_suit_class(grammar)
    states = list()

    initial_kernel = algo_suit.build_item(grammar.prods[grammar.start][0])
    states.append(LRState(frozenset({initial_kernel})))

    state_idx = 0
    while state_idx < len(states):
        src_state = states[state_idx]
        src_dict, dst_dict \
            = _construct_state_transition_dict(grammar, src_state, algo_suit)
        src_state.edges = _construct_edge(states, src_dict, dst_dict)
        state_idx += 1
    return states


def dump_dfa(states: list, export_file):
    export_file.write('digraph {\n  rankdir = "LR";')

    for i, state in enumerate(states):
        export_file.write('  "node{}" [\n'.format(i))
        export_file.write('    shape = "record"\n')
        export_file.write(r'    label = "I{}\n|'.format(i))
        export_file.write(r'\l'.join([str(t) for t in state.kernel]))
        nonkernel = state.get_closure() - state.kernel
        export_file.write(r'\l')
        if nonkernel:
            export_file.write('|')
            export_file.write(r'\l'.join([str(t) for t in nonkernel]))
            export_file.write(r'\l')
        export_file.write('"\n  ];\n')
    export_file.write('\n\n')
    for src_state, state in enumerate(states):
        for sym, edge in state.edges.items():
            if sym == '':
                continue
            line = '  "node{}" -> "node{}" [label="{}"]\n'.format(
                src_state, edge.dst_state, sym)
            export_file.write(line)

    export_file.write('}')


def str_states(states: list) -> str:
    result = '  States:'
    for i, state in enumerate(states):
        result += '\n    {}:'.format(i)
        for item in state.kernel:
            result += '\n      {}'.format(item)
        nonkernel = state.get_closure() - state.kernel
        if nonkernel:
            result += '\n      (Nonkernel)'
            for item in nonkernel:
                result += '\n      {}'.format(item)
    return result


def str_transitions(states: list) -> str:
    result = '  Transitions:'
    for src_state, state in enumerate(states):
        for sym, edge in state.edges.items():
            if sym == '':
                continue
            result += '\n    {} {} {}'.format(src_state, sym, edge.dst_state)
    return result


def str_lr(grammar: Grammar, algo_suit_class):
    states = construct_states(grammar, algo_suit_class)
    result = algo_suit_class.NAME + ':'
    result += '\n' + str_states(states)
    result += '\n' + str_transitions(states)
    return result


def dump_lr(grammar: Grammar, algo_suit_class, export_file):
    states = construct_states(grammar, algo_suit_class)
    dump_dfa(states, export_file)


def main():
    bnf = '''
    S := C C
    C := c C | d
    '''
    grammar = bnf_parser.parse(bnf)
    print(str_lr(grammar, LR1AlgorithmSuit))
    dump_lr(grammar, LR1AlgorithmSuit, open('dump.dot', 'w'))


if __name__ == '__main__':
    main()
