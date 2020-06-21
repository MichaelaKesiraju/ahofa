#!/usr/bin/env python3
# NFA reduction algorithms: pruning and merging

import networkx
import sys

from nfa import Nfa

def bfs(aut):
    '''
    Breadth first search of NFA.

    Parameters
    ----------
    aut : Nfa class
        the NFA to reduce
    '''

    reachable = set()
    queue = [aut._initial_state]
    reachable.add(aut._initial_state)
    while queue:
        q = queue.pop(0)        
        neighbours_of_q = set()
        for symbol in aut._transitions[q]:
            connected_states = aut._transitions[q][symbol]
            neighbours_of_q = neighbours_of_q.union(connected_states)
        queue.extend(neighbours_of_q - reachable)
        reachable = reachable.union(neighbours_of_q)
    return reachable


def pruning_v2(aut, ratio, freq):
    '''
    Pruning NFA reduction (in place).

    Parameters
    ----------
    aut : Nfa class
        the NFA to reduce
    ratio :
        reduction ratio
    freq : dict
        packet frequencies extracted from PCAS

    RETURNS
    -------
    max_err: int
        sum of frequencies of removed states
    '''
    
    depth = aut.state_depth
    states = set(aut.states) - set([aut._initial_state])
    # sorts states in ascending order of frequencies and in case of same 
    # frequency in the descending order of depth
    states = sorted(states, key=lambda x: (freq[x], depth[x]), reverse=False)
    orig_cnt = aut.state_count
    current_cnt = orig_cnt

    #how many states we want to keep is cnt
    target_cnt = int(round(ratio * orig_cnt))
    assert target_cnt > 1
    i = 0

    max_err = 0
    while current_cnt > target_cnt:
        f = freq[states[i]]
        R = []
        
        while freq[states[i]] == f:
            # put states with least frequency into set R
            R.append(states[i])
            q = states[i] 
            # put states from R into final states
            aut._add_final_state(states[i])
            # change transitions for states in R to selfloop over all alphabet
            for symbol in aut.alphabet:
                aut._transitions[q][symbol] = {q}
            i += 1
            if i == len(states):
                sys.stderr.write('Unusual scenario. No more states left but required reduction cannot be reached. \n')
                sys.exit()
        # breadth first search to identify unreachable states
        reachable_states = bfs(aut)
        current_cnt = len(reachable_states)
        #removing unreachable states
        unreachable = set(aut.states) - reachable_states
        aut._final_states -= unreachable
        
        for state in unreachable:
            max_err += freq[state]
            aut._transitions.pop(state, None) 
    return max_err      



def pruning(aut, ratio=.25, *, freq):
    '''
    Pruning NFA reduction (in place).

    Parameters
    ----------
    aut : Nfa class
        the NFA to reduce
    ratio :
        reduction ratio
    freq : str, None
        PCAP filename, or file with packet frequencies, or None
    
    '''
    #if not 0 < ratio < 1:
    #    raise RuntimeError('invalid reduction ratio value: ' + str(ratio))
    # import pdb
    # pdb.set_trace()
    depth = aut.state_depth
    states = set(aut.states) - aut._final_states - set([aut._initial_state])
    states = sorted(states, key=lambda x: (freq[x], -depth[x]), reverse=True)

    orig_cnt = aut.state_count
    #how many states we want to keep is cnt
    cnt = int(round(ratio * orig_cnt) - len(aut._final_states) - 1)
    # print("cnt:", cnt)
    assert cnt > 1
    fin = {}
    #making inverse dictionary,original is final state:all predecessor states
    #to all predecessor states:final state
    #next line means 
    # for f, ss in aut.fin_pred().items():
    #   for s in ss:
    #       fin[s] = f


    fin = {s:f for f,ss in aut.fin_pred().items() for s in ss}
    #mapping = {}
    #for s in states[cnt:]:
    #    mapping[s]=fin[s]
    #not all fin[s] will be there

    mapping = {s:fin[s] for s in states[cnt:]}
    
    aut.merge_states(mapping)


def merging(aut, *, th=.995, max_fr=.1, freq=None):
    '''
    Merging NFA reduction (in place).

    Parameters
    ----------
    aut : Nfa class
        the NFA to reduce
    freq : str, None
        PCAP filename, or file with packet frequencies, or None
    th :
        merging threshold
    mf :
        maximal frequency merging parameter

    Returns
    -------
    m
        the number of merged states
    '''    
    if freq == None: raise RuntimeError('packet frequency not provided')
    if not 0 <= th <= 1: raise RuntimeError('invalid threshold value')
    if not 0 <= max_fr <= 1: raise RuntimeError('invalid max_fr value')

    succ = aut.succ
    actual = set([aut._initial_state])
    visited = set([aut._initial_state])
    finals = aut._final_states

    mapping = {}
    marked = []
    #max(freq.values) is the highest value of packet frequency in training file, just a number withou a state
    max_ = max_fr * max(freq.values())#ten percent of max frequency
    # BFS
    while actual:
        new = set()
        for p in actual:
            freq_p = freq[p]
            t = freq_p / max_
            if not p in finals and freq_p != 0 and t <= max_fr:
                #selects the low frequency states based on this threshold
                for q in succ[p] - finals - set([p]):
                    freq_q = freq[q]
                    d = min(freq_q,freq_p) / max(freq_q,freq_p)
                    #the smaller one will be divided by the bigger one
                    if d > th and p != aut._initial_state: marked.append((p,q))
        #marks pairs of low frequency states
            new |= succ[p]
            #in new it adds all the children of p
        actual = new - visited
        visited |= new
    
    # handle transitivity
    g = networkx.Graph(marked)
    for cluster in networkx.connected_component_subgraphs(g):
        l = list(cluster.nodes())
        assert len(l) > 1
        for i in l[1:]: mapping[i] = l[0]
    
    aut.merge_states(mapping)
    # return the number of merged (removed) states
    return len(mapping)
