/// @author Jakub Semric
/// 2018

#include <iostream>
#include <ostream>
#include <vector>
#include <map>
#include <csignal>
#include <ctype.h>
#include <getopt.h>

#include "nfa.hpp"
#include "pcap_reader.hpp"
#include "reduction.hpp"

using namespace reduction;
using namespace std;

const char *helpstr =
"NFA reduction\n"
"Usage: ./reduce [OPTIONS] NFA FILE\n"
"options:\n"
"  -h            : show this help and exit\n"
"  -o <FILE>     : specify output file or directory for -s option\n"
"  -f            : don't reduce, but, compute packet frequency of NFA states\n"
"  -s            : use precomputed frequencies instead of pcap\n"
"  -t <N>        : frequency threshold for merging, default 0.995\n"
"  -i <N>        : number of iterations, default 0, which means pruning\n"
"  -r <N>        : reduction rate\n";

void check_float(float x, float max_val = 1, float min_val = 0)
{
    if (x > max_val || x < min_val) {
        throw runtime_error(
            "invalid float value: \"" + to_string(x) +
            "\", should be in range (" + to_string(min_val) + "," +
            to_string(max_val) + ")");
    }
}

int main(int argc, char **argv)
{
    // options
    bool freq_opt = false;
    float rratio = -1;
    float threshold = 0.995;
    size_t iter = 0;
    string outfile = "reduced-nfa.fa", pcap;
    bool pre = false;

    int opt_cnt = 1;    // program name
    int c;
    
    try {
        if (argc < 2) {
            cerr << helpstr;
            return 1;
        }

        while ((c = getopt(argc, argv, "ho:f:r:t:i:s")) != -1) {
            opt_cnt++;
            switch (c) {
                // general options
                case 'h':
                    cerr << helpstr;
                    return 0;
                case 'o':
                    outfile = optarg;
                    opt_cnt++;
                    break;
                case 'f':
                    freq_opt = true;
                    break;
                case 'r':
                    opt_cnt++;
                    rratio = stod(optarg);
                    check_float(rratio);
                    break;
                case 's':
                    pre = true;
                    break;
                case 't':
                    opt_cnt++;
                    threshold = stod(optarg);
                    check_float(threshold);
                    break;
                case 'i':
                    opt_cnt++;
                    iter = stoi(optarg);
                    break;
                default:
                    return 1;
            }
        }

        // checking the min. number of positional arguments, which is 2
        if (argc - opt_cnt < 2)
        {
            throw runtime_error("invalid positional arguments");
        }

        // get automata
        string nfa_str = argv[opt_cnt];
        string pcap = argv[opt_cnt + 1];

        FastNfa nfa;
        nfa.read_from_file(nfa_str.c_str());
        auto state_map = nfa.get_reversed_state_map();

        ofstream out{outfile};
        if (!out.is_open())
        {
            throw runtime_error("cannot open output file");
        }

        if (freq_opt)
        {
            auto freq = compute_freq(nfa, pcap);
            for (auto i : freq)
            {
                out << i.first << " " << i.second << endl;
            }
        }
        else
        {
            auto old_sc = nfa.state_count();
            auto res = reduce(nfa, pcap, rratio, threshold, iter, pre);
            auto new_sc = nfa.state_count();

            cerr << "Reduction: " << new_sc << "/" << old_sc
                << " " << 100 * new_sc / old_sc << "%\n";
            cerr << "Packet Error: " << res.first << endl;
            nfa.print(out);
        }

        cerr << "Saved as: " << outfile << endl;
        out.close();
    }
    catch (exception &e) {
        cerr << "\033[1;31mERROR\033[0m " << e.what() << endl;
        return 1;
    }

    return 0;
}
