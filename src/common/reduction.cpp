/// @author Jakub Semric
/// 2018

#include <iostream>
#include <sstream>
#include <algorithm>
#include <fstream>
#include <cassert>
#include <unistd.h>

#include "pcap_reader.hpp"
#include "aux.hpp"
#include "nfa.hpp"
#include "reduction.hpp"

namespace reduction {

using namespace std;

map<State, unsigned long> read_state_freq(const Nfa &nfa, const string &fname)
{
    map<State, unsigned long> ret;
    ifstream in{fname};
    if (!in.is_open()) {
        throw runtime_error("error loading NFA");
    }

    string buf;
    while (getline(in, buf)) {
        // remove '#' comment
        buf = buf.substr(0, buf.find("#"));
        if (buf == "") {
            continue;
        }
        istringstream iss(buf);
        State s;
        unsigned long l;
        if (!(iss >> s >> l)) {
            throw runtime_error("invalid state labels syntax");
        }
        if (!nfa.is_state(s)) {
            throw runtime_error("invalid NFA state: " + to_string(s));
        }
        ret[s] = l;
    }
    in.close();
    return ret;
}

map<State, unsigned long> compute_freq(
    const FastNfa &nfa, pcap_t *pcap, size_t count)
{
    map<State, unsigned long> freq;

    vector<size_t> state_freq(nfa.state_count());

    pcapreader::process_payload(
        pcap,
        [&] (const unsigned char *payload, unsigned len)
        {
            nfa.label_states(state_freq, payload, len);
        }, count);

    // remap frequencies
    auto state_map = nfa.get_reversed_state_map();
    for (unsigned long i = 0; i < nfa.state_count(); i++)
    {
        freq[state_map[i]] = state_freq[i];
    }

    return freq;
}

map<State, unsigned long> compute_freq(
    const FastNfa &nfa, string fname, size_t count)
{
    char err_buf[4096] = "";
    pcap_t *pcap;
    if (!(pcap = pcap_open_offline(fname.c_str(), err_buf))) 
        throw std::ios_base::failure("cannot open pcap file '" + fname + "'");

    return compute_freq(nfa, pcap, count);
}

float prune(
    Nfa &nfa, const map<State, unsigned long> &state_freq, float pct)
{
    assert((pct > 0 && pct <= 1) || pct == -1);

    map<State,State> merge_map;
    // merge only states with corresponding rule, which is defined by final
    // state
    auto rule_map = nfa.split_to_rules();
    auto depth = nfa.state_depth();

    // sort state_freq
    // mark which states to prune
    vector<State> sorted_states;
    State init = nfa.get_initial_state();
    // total packets
    size_t total = 0;

    for (auto i : state_freq)
    {
        if (!nfa.is_final(i.first) && i.first != init)
        {
            sorted_states.push_back(i.first);
        }
        total = total < i.second ? i.second : total;
    }

    try {
        // sort states in ascending order according to state packet frequencies
        // and state depth
        sort(
            sorted_states.begin(), sorted_states.end(),
            [&state_freq, &depth](State x, State y)
            {
                auto _x = state_freq.at(x);
                auto _y = state_freq.at(y);
                return  _x == _y ? depth.at(x) > depth.at(y) : _x < _y;
            });

        float error = 0;
        size_t state_count = nfa.state_count();
        size_t removed = 0;
        size_t to_remove = (1 - pct) * state_count;

        if (pct == -1)
        {
            // magic constant 0.001
            // error is quite inaccurate, sometimes it may deviate by 10 times
            while (error < 0.001)
            {
                State state = sorted_states[removed];
                merge_map[state] = rule_map[state];
                removed++;
                error += (1.0 * state_freq.at(state)) / total;
            }
        }
        else
        {
            while (removed < to_remove && removed < sorted_states.size())
            {
                State state = sorted_states[removed];
                merge_map[state] = rule_map[state];
                removed++;
                error += (1.0 * state_freq.at(state)) / total;
            }
        }

        nfa.merge_states(merge_map);

        return error;
    }
    catch (out_of_range &e)
    {
        string errmsg =
            "invalid index in state frequencies in 'prune' function ";
        errmsg += e.what();
        throw out_of_range(errmsg);
    }
}

int merge(
    Nfa &nfa, const map<State, unsigned long> &state_freq, float threshold)
{
    auto suc = nfa.succ();
    map<State,State> mapping;
    auto rules = nfa.split_to_rules();
    int cnt_merged = 0;
    set<State> to_merge;

    State init = nfa.get_initial_state();
    set<State> actual = suc[init];
    set<State> visited = suc[init];
    actual.erase(init);
    visited.insert(init);

    while (!actual.empty())
    {
        set<State> next;
        for (auto state : actual)
        {
            auto freq = state_freq.at(state);
            if (freq == 0)
            {
                continue;
            }
            for (auto next_state : suc[state])
            {
                if (visited.find(next_state) == visited.end())
                {
                    // too close to final state
                    bool cond = 1;
                    for (auto x : suc[next_state])
                    {
                        if (nfa.is_final(x))
                        {
                            cond = false;
                            break;
                        }
                    }
                    float diff = 1.0 * state_freq.at(next_state) / freq;
                    if (cond && diff >= threshold)
                    {
                        cnt_merged++;
                        if (mapping.find(state) != mapping.end())
                        {
                            mapping[next_state] = mapping[state];
                        }
                        else
                        {
                            mapping[next_state] = state;   
                        }
                    }
                    next.insert(next_state);
                    visited.insert(next_state);
                }
            }
        }
        actual = move(next);
    }
    // just for verification
    for (auto i : to_merge) {
        if (mapping.find(i) != mapping.end()) {
            throw runtime_error("FAILURE");
        }
    }
    if (!mapping.empty())
        nfa.merge_states(mapping);
    return cnt_merged;
}

void display_heatmap(const FastNfa &nfa, map<State,size_t> &freq)
{
    ofstream out1{"freq.txt"};
    for (auto i : freq)
    {
        out1 << i.first << " " << i.second << endl;
    }
    out1.close();
    ofstream out2{"automaton.fa"};
    nfa.print(out2);
    out2.close();
    if (system("python3 draw_nfa.py automaton.fa -f freq.txt") == -1)
    {
        cerr << "WARNING: cannot display automaton\n";
    }
}

pair<float,size_t> reduce(
    FastNfa &nfa, const string &samples, float pct, float th,
    size_t iterations, bool pre)
{
    size_t old_cnt = nfa.state_count();
    size_t count = 0;
    size_t merged = 0;
    map<State,size_t> state_freq;

    if (pre || iterations < 2)
    {
        state_freq = pre ? read_state_freq(nfa, samples) :
                           compute_freq(nfa, samples);
        if (iterations > 0)
        {
            // just 1 merge
            merged = merge(nfa, state_freq, th);
        }
    }
    else
    {
        pcap_t *pcap = 0;
        char err_buf[4096] = "";
        // open pcap
        if (!(pcap = pcap_open_offline(samples.c_str(), err_buf))) 
        {
            throw std::ios_base::failure(
                "cannot open pcap file '" + samples + "'");
        }
        // compute count
        pcapreader::process_payload(
            samples.c_str(),
            [&] (const unsigned char *payload, unsigned len)
            { (void)payload; (void)len; count++; });

        count /= iterations;
        //assert(count > 1000);

        while (iterations-- > 0)
        {
            // compute freq
            state_freq = compute_freq(nfa, pcap, count);

            #if 0
            display_heatmap(nfa2, freq);
            sleep(4);
            #endif
            
            // compute % reduction in each turn
            merged += merge(nfa, state_freq, th);
            nfa.build();

            #if 0
            cerr << "Merged: " << merged << endl;
            cerr << "-----\n";
            #endif
        }
    }
    // change the reduction ratio in order to adjust pruning
    if (pct != -1)
    {
        size_t new_cnt = nfa.state_count();
        assert(old_cnt >= new_cnt);
        pct -= pct - old_cnt * pct / new_cnt;
    }

    // adjust state frequencies, remove merged states
    map<State, size_t> freq;
    for (auto i : state_freq)
    {
        if (nfa.is_state(i.first))
        {
            freq[i.first] = i.second;
        }
    }

    float er = prune(nfa, freq, pct);
    return pair<float,size_t>(er, merged);
}

}
