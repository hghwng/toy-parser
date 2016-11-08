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


class LRAction:
    SHIFT = 1,
    REDUCE = 2,
    GOTO = 3,
    ACCEPT = 4,

    def __init__(self, action: int, info=None):
        self.action = action
        self.info = info

    def __repr__(self):
        if self.action == self.SHIFT:
            return "LRAction(SHIFT, {})".format(self.info)
        if self.action == self.REDUCE:
            return "LRAction(REDUCE, {})".format(self.info)
        if self.action == self.GOTO:
            return "LRAction(GOTO, {})".format(self.info)
        if self.action == self.ACCEPT:
            return "LRAction(ACCEPT)"
        assert False

    def __str__(self):
        if self.action == self.SHIFT:
            return "Shift {}".format(self.info)
        if self.action == self.REDUCE:
            return "Reduce {}".format(self.info)
        if self.action == self.GOTO:
            return "Goto {}".format(self.info)
        if self.action == self.ACCEPT:
            return "Accept"
        assert False

    @staticmethod
    def new_shift(state: int):
        return LRAction(LRAction.SHIFT, state)

    @staticmethod
    def new_reduce(prod: Production):
        return LRAction(LRAction.REDUCE, prod)

    @staticmethod
    def new_goto(state: int):
        return LRAction(LRAction.GOTO, state)

    @staticmethod
    def new_accept():
        return LRAction(LRAction.ACCEPT)


class LR0AlgorithmSuit:
    NAME = 'LR(0)'

    def __init__(self, grammar: Grammar):
        self.grammar = grammar

    def build_item(self, prod: Production, parent: LR0Item=None):
        self = self
        parent = parent
        return LR0Item(prod)

    def build_reduce(self, actions: defaultdict, edge: LREdge):
        # Just simply reduce!
        for item in edge.src_items:
            for term in self.grammar.terms:
                actions[term].add(LRAction.new_reduce(item.prod))


class SLR1AlgorithmSuit(LR0AlgorithmSuit):
    NAME = 'SLR(1)'

    def __init__(self, grammar: Grammar):
        LR0AlgorithmSuit.__init__(self, grammar)
        first = ll1.construct_first(grammar)
        self.follow = ll1.construct_follow(grammar, first)

    def build_reduce(self, actions: defaultdict, edge: LREdge):
        # Reduce by consulting the FOLLOW set
        for item in edge.src_items:
            for term in self.follow[item.prod.nterm]:
                actions[term].add(LRAction.new_reduce(item.prod))


class LR1AlgorithmSuit:
    NAME = 'LR(1)'

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

    def build_reduce(self, actions: defaultdict, edge: LREdge):
        self = self
        for item in edge.src_items:
            for lookahead in item.lookahead:
                actions[lookahead].add(LRAction.new_reduce(item.prod))


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


def construct_states(grammar: Grammar, algo_suit):
    states = list()
    initial_kernel = algo_suit.build_item(grammar.get_start_prodctions()[0])
    states.append(LRState(frozenset({initial_kernel})))

    state_idx = 0
    while state_idx < len(states):
        src_state = states[state_idx]
        src_dict, dst_dict \
            = _construct_state_transition_dict(grammar, src_state, algo_suit)
        src_state.edges = _construct_edge(states, src_dict, dst_dict)
        state_idx += 1
    return states


def construct_table(grammar: Grammar, states: list, algo_suit):
    final_item = LR0Item(grammar.get_start_prodctions()[0], 1)
    table = list()  # table[src_state][sym] = set(LRAction)
    for state in states:
        actions = defaultdict(set)
        table.append(actions)
        for sym, edge in state.edges.items():
            if sym == '':
                continue
            if grammar.is_terminal(sym):
                # Terminal, shift
                actions[sym].add(LRAction.new_shift(edge.dst_state))
            else:
                # Nonterminal, goto
                actions[sym].add(LRAction.new_goto(edge.dst_state))
        if '' in state.edges:
            edge = state.edges['']
            current_item = tuple(edge.src_items)[0]
            if final_item.prod == current_item.prod and \
               final_item.pos == current_item.pos:
                # Accept
                actions['$'].add(LRAction.new_accept())
            else:
                # Reduce
                algo_suit.build_reduce(actions, edge)
    return table


def parse(table: list, input_syms: list, callback):
    states = [0]
    syms = ['$']
    pos = 0

    while True:
        if pos < len(input_syms):
            sym = input_syms[pos]
        else:
            sym = '$'
        state = states[-1]
        action = tuple(table[state][sym])[0]
        if action.action == LRAction.SHIFT:
            callback(action, states, syms, pos)
            states.append(action.info)
            syms.append(sym)
            pos += 1
            if pos > len(input_syms):
                pos = len(input_syms)
        elif action.action == LRAction.REDUCE:
            callback(action, states, syms, pos)
            length = len(action.info.syms)
            syms = syms[:-length] + list(action.info.nterm)
            states = states[:-length]
            goto_action = tuple(table[states[-1]][action.info.nterm])[0]
            assert goto_action.action == LRAction.GOTO
            states.append(goto_action.info)
        elif action.action == LRAction.ACCEPT:
            callback(action, states, syms, pos)
            return
        else:
            assert False


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


def str_table(table: list):
    result = '  Table:'
    for src_state, row in enumerate(table):
        for sym, actions in row.items():
            header = '{} - {}'.format(src_state, sym)
            for action in actions:
                result += '\n    ' + header + ': ' + str(action)
                header = '!' * len(header)
    return result


def str_lr(grammar: Grammar, algo_suit_class):
    grammar = construct_argumented_grammar(grammar)
    algo_suit = algo_suit_class(grammar)
    states = construct_states(grammar, algo_suit)
    table = construct_table(grammar, states, algo_suit)

    result = algo_suit_class.NAME + ':'
    result += '\n' + str_states(states)
    result += '\n' + str_transitions(states)
    result += '\n' + str_table(table)
    return result


def dump_lr(grammar: Grammar, algo_suit_class, export_file):
    algo_suit = algo_suit_class(grammar)
    grammar = construct_argumented_grammar(grammar)
    states = construct_states(grammar, algo_suit)
    dump_dfa(states, export_file)


def _demo_parse_cptt(table: list, input_syms: list):
    stack_str = list()
    symbol_str = list()
    input_str = list()
    action_str = list()
    def callback(action, states, syms, pos):
        stack_str.append(' '.join([str(i) for i in states]))
        symbol_str.append(' '.join(syms))
        input_str.append(' '.join(input_syms[pos:]))
        action_str.append(str(action))
    parse(table, input_syms, callback)

    get_length = lambda arr: max([len(t) for t in arr])
    stack_length = get_length(stack_str)
    symbol_length = get_length(symbol_str)
    input_length = get_length(input_str)
    for i, input_val in enumerate(input_str):
        print('{} | {} | {} $ | {}'.format(
            stack_str[i].ljust(stack_length),
            symbol_str[i].ljust(symbol_length),
            input_val.rjust(input_length),
            action_str[i]))

def _demo_parse_old(table: list, input_syms: list):
    overview_str = list()
    input_str = list()
    action_str = list()
    def callback(action, states, syms, pos):
        overview = str(states[0])
        for i, sym in enumerate(syms[1:]):
            overview += ' ' + str(sym) + ' ' + str(states[i + 1])
        input_str.append(' '.join(input_syms[pos:]))
        overview_str.append(overview)
        action_str.append(action)
    parse(table, input_syms, callback)

    get_length = lambda arr: max([len(t) for t in arr])
    overview_length = get_length(overview_str)
    input_length = get_length(input_str)
    for i, input_val in enumerate(input_str):
        print('{} | {} | {}'.format(
            overview_str[i].ljust(overview_length),
            input_val.rjust(input_length),
            action_str[i]))


def demo_parse(grammar: Grammar, algo_suit_class, input_syms: list,
               old_style=True):
    grammar = construct_argumented_grammar(grammar)
    algo_suit = algo_suit_class(grammar)
    states = construct_states(grammar, algo_suit)
    table = construct_table(grammar, states, algo_suit)
    print(str_states(states))
    print(str_table(table))
    if old_style:
        _demo_parse_old(table, input_syms)
    else:
        _demo_parse_cptt(table, input_syms)


def main():
    bnf = '''
    E := E + T | T
    T := T * F | F
    F := ( E ) | id
    '''
    grammar = bnf_parser.parse(bnf)
    # print(str_lr(grammar, SLR1AlgorithmSuit))
    demo_parse(grammar, SLR1AlgorithmSuit, 'id * id + id'.split())


if __name__ == '__main__':
    main()
