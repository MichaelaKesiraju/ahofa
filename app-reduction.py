#!/usr/bin/env python3
# Approximate NFA reduction and error evaluation of the reduction NFA.



import os
import sys
import tempfile
import argparse
import multiprocessing

from nfa import Nfa
from reduction_eval import reduce_nfa, armc

#takes arguments and puts into two different variables because they are mutualy exclusive
def main():
    parser = argparse.ArgumentParser(description='Approximate NFA reduction.')
    parser.add_argument('-r','--ratio', metavar='N', type=float,
        default=.2, help='reduction ratio')
    parser.add_argument('input', type=str, help='NFA to reduce')
    parser.add_argument('-n','--nw', type=int,
        default=multiprocessing.cpu_count() - 1,
        help='number of workers to run in parallel')
    parser.add_argument('--test', nargs='+', type=str,  metavar='PCAP',
        help='test pcap files')
    parser.add_argument('--train', type=str, metavar='PCAP',
        help='train pcap file')

    group = parser.add_mutually_exclusive_group()
    #action store true means if given store true else store false
    group.add_argument('-m','--merge', action='store_true',
        help='merging reduction')
    group.add_argument('-a','--armc', action='store_true',
        help='merging reduction inspired by abstract regular model checking')
    
    parser.add_argument('-fp', '--freq_pruning', action='store_true',
        help='frequency based pruning reduction (not tested in combination with -m merge)')
    parser.add_argument('-th','--thresh', type=float, metavar='N',
        help='threshold for merging', default=.995)
    parser.add_argument('-mf','--maxfr', type=float, default=.1,
         metavar='N', help='max frequency of a state allowed to be merged')
    parser.add_argument('-o','--output', type=str,default='output.fa')
    args = parser.parse_args()

    if (args.merge or args.armc) and not args.train:
        raise SystemError('--train option is required when merging')
    
    #saving results for later automatic testing
    prune = "p"
    if args.freq_pruning:
        prune = "fp"

    os.makedirs("results", exist_ok = True)

    results_file = f"results/{os.path.basename(args.train)}_{os.path.basename(args.input)}_{prune}_{args.ratio}.txt"

    if os.path.exists(results_file):
        print(results_file, "already exists.")
        sys.exit()
    # get NFA
    #takes nfa from input and in class Nfa is uses function parse, which reads it
    aut = Nfa.parse(args.input)
        

    if args.armc:
        # method of merging.merge using armc and prune, uses similare state of prefixes
        #armc function returns two values. aut and m(number of states merged)
        aut, m = armc(aut, args.train, ratio=args.ratio, th=args.thresh,
            merge_empty=False)
        sys.stderr.write('states merged: ' + str(m) + '\n')
    else:
        #if there is no armc it comes here
        #if -m not given it does just pruning(happens inside reduce_nfa, merge=args.merge )
        #if ratio not given it is .2 by default
        sys.stderr.write('reduction ratio: ' + str(args.ratio) + '\n')
        #get_freq is in nfa.py inside Nfa class
        #it knows what is in nfa and using train it calculates frequency
        #returns dictionary, so freq is dictionary, state:frequency

        #it computes state frequency, how many times has state been visited, returns dictionary,state and number
    #REMOVE LATER  FREQ_FILE=TRUE
        freq = aut.get_freq(args.train, freq_file=False)
                
        #second method of merging, uses state frequency
        aut, m , max_err = reduce_nfa(aut, freq, ratio=args.ratio, merge=args.merge, freq_pruning=args.freq_pruning,
            th=args.thresh, mf=args.maxfr)
        if args.merge:
            sys.stderr.write('states merged: ' + str(m) + '\n')
    #writes reduced nfa into file
    with open(args.output,'w') as f:
        sys.stderr.write('saved as ' + args.output + '\n')
        aut.print(f)
    #it computes the reduction error
    if args.test:
        sys.stderr.write('evaluation reduction error\n')
        #reduced is not used further, but it puts the name of the output file, as given in arguments
        reduced = args.output
        #function of class Nfa, in file nfa.py, calls external program for err evaluation nfa_eval it is c++
        #we can run nfa_eval by ourselves
        #returns string of values, separated by comma
        r = Nfa.eval_accuracy(args.input, args.output, ' '.join(args.test),
            nw=args.nw)
        total, fp, tp = 0, 0, 0
        #r has many lines and each line has commas, separates by lines
        for b in r.split('\n'):
            #for every line in r, if not emlty it devides by comma and it has 7values and we want only 3 of them
            # rest is lost
            if b != '':
                _, _, s1, _, _, s2, s3 = b.split(',')
                total += int(s1)
                fp += int(s2)
                tp += int(s3)
        real_err = round(fp/total,4) 
        print('real error:', round(fp/total,4))

        estim_err = -1
        if max_err != -1:
            #divivde by sum of freq of all final states of original automata
            estim_err = round(max_err/total,4)
            print('estimated error of freq pruning', round(max_err/total,4))
        if tp + fp > 0:
            precis = round(tp/(fp+tp),4) 
            print('precision:', round(tp/(fp+tp),4))
            #4 means 4 decimal numbers in the funcion round()

        with open(results_file, 'w') as fptr:
            fptr.write("#real_error, precision, estimated_error\n")
            fptr.write(f"{real_err},{precis},{estim_err}\n")

        print(results_file,"saved.")
if __name__ == '__main__':
    main()