#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
import re
import os
from scipy.stats import zscore

def print_outliers(df):
    # compute zscore
    df['ce'] = (df['cls2'] - df['cls1']) / df['total']
    df_gr = df.groupby(['reduction','states'])[['ce']].transform(zscore)
    outliers = df_gr['ce'] > 3
    print(df.loc[outliers,['ce','pcap']])

def aggr_error(fname):
    df = pd.read_csv(fname)
    df = df.drop_duplicates()
    # aggregate all values for each reduction
    df_aggr = df.groupby('reduction')[
        ['acc1','acc2','cls1','cls2','wrong','correct','total']].sum()
    # compute other statistics
    df_aggr['error'] = (df_aggr['wrong'] / df_aggr['total'])
    return df_aggr

def compare_errors(fname1, fname2, kind='scatter'):
    df1 = aggr_error(fname1)
    df2 = aggr_error(fname2)
    plt.style.use('ggplot')

    ax = df1.reset_index().plot(
        x='reduction', y='error', color='Red', label='merge', marker='o',
        kind=kind, s=50)
    df2.reset_index().plot(
        x='reduction', ax=ax, y='error', label='prune', marker='D', kind=kind,
        s=50)

    plt.xlim(0.09,0.23)
#    plt.ylim(-0.001,0.035)
    plt.margins(0.05,0.05)
    #plt.grid()
    title = os.path.basename(re.sub('-merge.*','',fname1))
    plt.title(title)
    plt.xlabel('reduction ratio')
    plt.ylabel('error')
    plt.show()

def plot_errors(fname):
    df = aggr_error(fname)
    # plotting the results
    plt.style.use('ggplot')
    # displaying only values in reasonable ranges
    filt = (df_aggr['error'] < 0.3) & (df_aggr['error'] > 0.00005)
    df_aggr[filt].plot(y='error', marker='o')
    # setting axis ranges
    plt.xlim(0.12,0.32)
    plt.ylim(-0.01,0.27)
    #plt.grid()
    plt.title(
        'sprobe error (' + format(int(df_aggr.iloc[0]['total']),',') + ')')
    plt.xlabel('reduction ratio')
    plt.ylabel('error')
    plt.show()

def main():
#    plot_errors('data/sprobe.csv')
#    pcap_analysis()
    compare_errors(sys.argv[1],sys.argv[2])

def pcap_analysis(fname='mc.txt'):
    # read with mixed data type, numpy stores result in 1d structured array
    data = np.log10(np.loadtxt(open(fname,'r'), delimiter=' '))
    close(filename)
    plt.imshow(data, cmap='jet', interpolation='nearest')
    plt.colorbar()
    plt.show()

if __name__ == "__main__":
    main()
