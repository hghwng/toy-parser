#!/usr/bin/env python
from grammar import Grammar, Production


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
        return LR0Item(self.prod, self.pos + 1)

    def __repr__(self):
        return "LR0Item({}, {})".format(self.prod, self.pos)

    def __str__(self):
        dot_syms = list(self.prod.syms)
        dot_syms.insert(self.pos, '·')
        return "{} → {}".format(self.prod.nterm, " ".join(dot_syms))


class LR0Constructor:
    def __init__(self, grammar: Grammar):
        self.grammar = LR0Constructor._construct_argumented_grammar(grammar)
        self.closures = list()      # closures[state] = set(item)
        self.kernels = list()       # kernels[state] = set(kernel_item)

        goto = self._construct_goto_and_kernels_and_closures()
        # transitions[src_state][sym] = dst_state
        self.transitions = self._construct_transitions(goto)

    def __str__(self):
        result = 'LR(0):'
        result += '\n  States:'
        for i, kernel in enumerate(self.kernels):
            result += '\n    {}:'.format(i)
            for item in kernel:
                result += '\n      {}'.format(item)
            nonkernel = self.closures[i] - kernel
            if nonkernel:
                result += '\n      (Nonkernel)'.format(i)
                for item in nonkernel:
                    result += '\n      {}'.format(item)

        result += '\n  Transitions:'
        for src_state, transitions in enumerate(self.transitions):
            for sym, dst_state in transitions.items():
                result += '\n    {} {} {}'.format(src_state, sym, dst_state)
        return result

    def dump(self, export_file):
        export_file.write('digraph {\n  rankdir = "LR";')

        for i, kernel in enumerate(self.kernels):
            export_file.write('  "node{}" [\n'.format(i))
            export_file.write('    shape = "record"\n')
            export_file.write(r'    label = "I{}\n|'.format(i))
            export_file.write(r'\l'.join([str(t) for t in kernel]))
            nonkernel = self.closures[i] - kernel
            export_file.write(r'\l')
            if nonkernel:
                export_file.write('|')
                export_file.write(r'\l'.join([str(t) for t in nonkernel]))
                export_file.write(r'\l')
            export_file.write('"\n  ];\n')
        export_file.write('\n\n')
        for src_state, transitions in enumerate(self.transitions):
            for sym, dst_state in transitions.items():
                line = '  "node{}" -> "node{}" [label="{}"]\n'.format(
                    src_state, dst_state, sym)
                export_file.write(line)

        export_file.write('}')

    def _construct_argumented_grammar(grammar: Grammar) -> Grammar:
        START_NTERM = '!S'
        g = grammar.duplicate()
        g.add_production(START_NTERM, (g.start))
        g.start = START_NTERM
        return g

    def _get_closure(self, item) -> set:
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
               not self.grammar.is_nonterminal(next_syms[0]):
                continue
            for prod in self.grammar.prods[next_syms[0]]:
                new_item = LR0Item(prod)
                if new_item not in result:
                    new_items.add(new_item)
        return result

    def _construct_goto_and_kernels_and_closures(self):
        start_prod = self.grammar.prods[self.grammar.start][0]
        new_items = {frozenset({LR0Item(start_prod)})}
        old_items = set()

        #      goto[src_state_idx][sym] = set(dst_kernel_item)
        # self.goto[src_state_idx][sym] = dst_state_idx
        goto = list()
        while new_items:
            src_items = new_items.pop()
            old_items.add(src_items)
            self.kernels.append(src_items)

            closure_items_set = self._get_closure(src_items)
            self.closures.append(frozenset(closure_items_set))

            closure_items = list(closure_items_set)
            transitions = dict()
            for i, item in enumerate(closure_items):
                next_syms = item.get_syms_after_dot()
                if not next_syms:
                    continue
                next_sym = next_syms[0]
                if next_sym in transitions:
                    continue

                dst_items = set()
                for item in closure_items[i:]:
                    next_syms = item.get_syms_after_dot()
                    if not next_syms or next_syms[0] != next_sym:
                        continue
                    dst_items.add(item.get_advanced_item())

                dst_items = frozenset(dst_items)
                transitions[next_sym] = dst_items
                if dst_items not in old_items:
                    new_items.add(dst_items)
            goto.append(transitions)
        return goto

    def _construct_transitions(self, goto):
        result = [dict() for i in range(len(goto))]
        lookup = dict([(kernel, i)for i, kernel in enumerate(self.kernels)])

        for src_state, src_transitions in enumerate(goto):
            result_dict = result[src_state]
            for sym, dst_kernel in src_transitions.items():
                result_dict[sym] = lookup[dst_kernel]
        return result


def main():
    bnf = '''
    E := E + T | T
    T := T * F | F
    F := ( E ) | id
    '''
    from bnf_parser import parse
    grammar = parse(bnf)
    print(grammar)
    constructor = LR0Constructor(grammar)
    print(constructor)
    constructor.dump(open('dump.dot', 'w'))

if __name__ == '__main__':
    main()
