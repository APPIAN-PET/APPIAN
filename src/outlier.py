import numpy as np
import scipy as sp
import matplotlib
matplotlib.use('Agg')
from math import ceil
import matplotlib.pyplot as plt
from sys import exit
from scipy.stats import gaussian_kde
import sklearn
import pandas as pd
from scipy.integrate import simps
sklearn_major_version = float(sklearn.__version__.split('.')[1])
from sklearn.neighbors import KernelDensity

def kde(z, cdf=False, bandwidth=0.3):
    #print(z)
    z = np.array(z)
    #Set NaN values to 0
    z[np.isnan(z)]=0

    std = z.std(axis=0)

    if std == 0 or np.isnan(std) :
        std = 1

    z= (z - z.mean(axis=0)) / std
    factor=1
    #euc_dist = np.array([np.sqrt(np.sum((p-np.min(z,axis=0))**2))  for p in z] ).reshape(-1,1)
    if len(z.shape) == 2 :
        euc_dist = np.mean(z, axis=1).reshape(-1,1)
    else :
        euc_dist = z.reshape(-1,1)
    #print(euc_dist)

    kde = KernelDensity(bandwidth=bandwidth).fit(euc_dist)
    density = np.exp(kde.score_samples(euc_dist)).reshape(-1,1)
    min_euc_dist = min(euc_dist) #* -factor #0
    max_euc_dist = max(euc_dist) #* factor
    dd = np.linspace(min_euc_dist,max_euc_dist).reshape(-1,1)
    n=int(len(dd))

    ddx=(max_euc_dist-min_euc_dist)/n
    lin_density=np.exp(kde.score_samples(dd)).reshape(-1,1)
    n=len(density)
    cum_dense=np.zeros(n).reshape(-1,1)
    dd_range = range(len(dd))

    if not cdf :
        for ed,i in zip(euc_dist,range(n)):
            cum_dense[i] = np.sum([ lin_density[j] for j in dd_range if abs(dd[j]) > abs(ed) ]) * ddx
        return (cum_dense)

    for ed,i in zip(euc_dist,range(n)):
        cum_dense[i] = np.sum([ lin_density[j] for j in dd_range if dd[j] < ed]) * ddx

    return(cum_dense)



def MAD(z):
    z = np.array(z)
    if len(z.shape) == 1 :
        z=z.reshape(-1,1)
    z=(z - z.mean(axis=0))/z.std(axis=0)
    z=np.apply_along_axis( lambda x : np.sqrt(np.sum(x**2)) , 1, z)
    z=abs((z - np.median(z)) / (0.001+np.median(np.abs(z - np.median(z)))))
    z= 1/(0.1 + z)
    return z
