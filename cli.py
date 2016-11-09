#!/usr/bin/env python
import sys
import argparse
import ll1
import lr
import bnf_parser
import left_recursion_eliminator


def parse_input(args):
    parser = argparse.ArgumentParser(
        description='Demonstrate processing and parsing of various grammars.')
    parser.add_argument('bnf', metavar='BNF_FILE',
                        help='The input grammar written in BNF')
    parser.add_argument('-e', '--left-elim', action='store_true',
                        help='Eliminate left recursion on the input grammar')
    parser.add_argument('-g', '--grammar', action='store_true',
                        help='Print the parsed BNF')
    parser.add_argument('-f', '--first', action='store_true',
                        help='Print the FIRST set')
    parser.add_argument('-F', '--follow', action='store_true',
                        help='Print the FOLLOW set')

    parser.add_argument('--ll1-table', action='store_true',
                        help='Print the LL(1) table')
    parser.add_argument('--ll1-conflict', action='store_true',
                        help='Print conflicts in the LL(1) table')

    parser.add_argument('--lr-arg-grammar', action='store_true',
                        help='Print the argumented LR grammar')
    parser.add_argument('--lr0-state', action='store_true',
                        help='Print LR(0) states')
    parser.add_argument('--lr0-table', action='store_true',
                        help='Print LR(0) table')
    parser.add_argument('--lr0-transition', action='store_true',
                        help='Print LR(0) transitions')
    parser.add_argument('--lr0-dfa', action='store_true',
                        help='Export the LR(0) DFA graph')

    parser.add_argument('--slr1-table', action='store_true',
                        help='Print SLR(1) table')
    parser.add_argument('--slr1-dfa', action='store_true',
                        help='Export the SLR(1) DFA graph to')

    parser.add_argument('--lr1-state', action='store_true',
                        help='Print LR(1) states')
    parser.add_argument('--lr1-table', action='store_true',
                        help='Print LR(1) table')
    parser.add_argument('--lr1-transition', action='store_true',
                        help='Print LR(1) transitions')
    parser.add_argument('--lr1-dfa', action='store_true',
                        help='Export the LR(1) DFA graph')

    parser.add_argument('--parse-old', action='store_true',
                        help='Demonstrate LR parsing in the old style')
    parser.add_argument('--parse-ll1', dest='ll1_sym', metavar='SYM_FILE',
                        help='Demonstrate the parsing of the LL(1) grammar')
    parser.add_argument('--parse-lr0', dest='lr0_sym', metavar='SYM_FILE',
                        help='Demonstrate the parsing of the LR(0) grammar')
    parser.add_argument('--parse-slr1', dest='slr1_sym', metavar='SYM_FILE',
                        help='Demonstrate the parsing of the SLR(1) grammar')
    parser.add_argument('--parse-lr1', dest='lr1_sym', metavar='SYM_FILE',
                        help='Demonstrate the parsing of the LR(1) grammar')
    return parser.parse_args(args)


def process_ll(args, get):
    if args.first or args.follow or args.ll1_table or args.ll1_conflict:
        print('LL(1):')
    if args.first:
        print(ll1.str_first(get('grammar'), get('first')))
    if args.follow:
        print(ll1.str_follow(get('grammar'), get('follow')))
    if args.ll1_table:
        print(ll1.str_table(get('ll1_table')))
    if args.ll1_conflict:
        print(ll1.str_conflicts(get('ll1_conflict')))


def process_lr(args, get):
    if args.lr_arg_grammar:
        print('LR:')
        print(get('lr_grammar'))

    if args.lr0_state or args.lr0_transition or args.lr0_table:
        print('LR(0):')
    if args.lr0_state:
        print(lr.str_states(get('lr0_state')))
    if args.lr0_transition:
        print(lr.str_transitions(get('lr0_state')))
    if args.lr0_table:
        print(lr.str_table(get('lr0_table')))
    if args.lr0_dfa:
        lr.dump_dfa(get('lr0_state'), open(args.bnf + '.lr0.dot', 'w'))

    if args.slr1_table:
        print('SLR(1):')
        print(lr.str_table(get('slr1_table')))


def process_lr1(args, get):
    if args.lr1_state or args.lr1_transition or args.lr1_table:
        print('LR(1):')
    if args.lr1_state:
        print(lr.str_states(get('lr1_state')))
    if args.lr1_transition:
        print(lr.str_transitions(get('lr1_state')))
    if args.lr1_table:
        print(lr.str_table(get('lr1_table')))
    if args.lr1_dfa:
        lr.dump_dfa(get('lr1_state'), open(args.bnf + '.lr1.dot', 'w'))


def process_parse(args, get):
    get_syms = lambda path: open(path).read().split()
    if args.ll1_sym:
        print('Parse of LL(1):')
        print(ll1.str_parse(get('grammar'), get('ll1_table'), get_syms(args.ll1_sym)))
    if args.lr0_sym:
        print('Parse of LR(0):')
        print(lr.str_parse(get('lr0_table'), get_syms(args.lr0_sym), args.parse_old))
    if args.slr1_sym:
        print('Parse of SLR(1):')
        print(lr.str_parse(get('slr1_table'), get_syms(args.slr1_sym), args.parse_old))
    if args.lr1_sym:
        print('Parse of LR(1):')
        print(lr.str_parse(get('lr1_table'), get_syms(args.lr1_sym), args.parse_old))


def main():
    args = parse_input(sys.argv[1:])
    grammar = bnf_parser.parse(open(args.bnf).read())

    if args.left_elim:
        grammar = left_recursion_eliminator.eliminate(grammar)
    if args.grammar:
        print(grammar)

    context = dict(grammar=grammar)
    builder = dict(
        first=lambda: ll1.construct_first(grammar),
        follow=lambda: ll1.construct_follow(grammar, get('first')),
        ll1_table=lambda: ll1.construct_table(grammar, get('first'), get('follow')),
        ll1_conflict=lambda: ll1.construct_conflicts(get('ll1_table')),

        lr_grammar=lambda: lr.construct_argumented_grammar(grammar),
        lr0_suit=lambda: lr.LR0AlgorithmSuit(get('lr_grammar')),
        slr1_suit=lambda: lr.SLR1AlgorithmSuit(get('lr_grammar')),
        lr1_suit=lambda: lr.LR1AlgorithmSuit(get('lr_grammar')),

        lr0_state=lambda: lr.construct_states(get('lr_grammar'), get('lr0_suit')),
        lr1_state=lambda: lr.construct_states(get('lr_grammar'), get('lr1_suit')),
        lr0_table=lambda: lr.construct_table(get('lr_grammar'), get('lr0_state'), get('lr0_suit')),
        lr1_table=lambda: lr.construct_table(get('lr_grammar'), get('lr1_state'), get('lr1_suit')),
        slr1_table=lambda: lr.construct_table(get('lr_grammar'), get('lr0_state'),
                                              get('slr1_suit')),
    )

    def get(key):
        if key not in context:
            context[key] = builder[key]()
        return context[key]

    process_ll(args, get)
    process_lr(args, get)
    process_lr1(args, get)
    process_parse(args, get)

if __name__ == '__main__':
    main()
