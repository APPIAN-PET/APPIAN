import numpy as np
import scipy as sp
import matplotlib
matplotlib.use('TkAgg')
from math import ceil
import matplotlib.pyplot as plt
from sys import exit
from scipy.stats import gaussian_kde
from sklearn.neighbors.kde import KernelDensity

def dist(x0, x1):
    return( np.sqrt( np.sum((x0-x1)**2)) )


def k_dist(p1, k=0):
    n=len(p1)
    if k ==0:
        if n==2: k=1
        else: k=1+ceil(n * 0.05)
    kd=np.zeros(n)
    minPts=[]
    idx=[]
    k=int(k)
    l_r_range = range(n)
    for i in np.arange(len(p1), dtype=int) :
        i=int(i)
        d0 = map(lambda p : dist(p1[i], p), p1)
        idx0 = [ x for (y,x) in sorted(zip(d0,l_r_range)) ]
        d1 = np.sort(d0)
        kd[i] = d1[k]
        idx += [ idx0[1:k] ]
        minPts += [ d1[1:k] ]

    return([kd, idx, minPts])
                                                                                        
def local_reach_dist(p, idx, minPts, kd):
    lrd=[]
    for i in range(len(p)):
        m = minPts[i]
        index = idx[i]
        k = kd[i]
        pvar = p[i]
        n=len(m)

        s = np.sum( [ max( kd[index[j]], dist(p[index[j]],p[i]) ) for j in range(n)  ] )
        if s == 0 : val =0
        else: val = n / s
        lrd += [val]
    return( lrd )

def local_outlier_factor(lrd, idx, minPts):
    lcf=[]
    for i in range(len(lrd)):
        m = minPts[i]
        n = len(m)
        index = idx[i]
        s = np.sum([lrd[index[j]] for j in range(n)  ]) / lrd[i]
        if n != 0 : val=(lrd[i]/s)/n
        else: val=0
        lcf += [val]
    lcf = np.array(lcf).reshape(-1,1)
    return(lcf)

def lof(z, k=0):
    z= (z - z.mean(axis=0)) /  z.std(axis=0) 
 
    [kd,idx, minPts ] = k_dist(z, k)
    lrd = local_reach_dist(z, idx, minPts, kd)
    lcf = local_outlier_factor(lrd, idx, minPts)
    lcf = -np.log10( lcf )
    out = np.array(lcf)
    euc_dist = np.array( [ np.sqrt(np.sum((p-np.min(z,axis=0))**2))  for p in z] ).reshape(-1,1)
    euc_dist /= np.max(euc_dist)
    #euc_dist = np.random.normal(0, 1, len(euc_dist)).reshape(-1,1)
    temp=np.array(np.concatenate([lcf,euc_dist],axis=1))
    #kde0 = KernelDensity(bandwidth=0.9).fit(lcf)
    #kde1 = KernelDensity(bandwidth=0.9).fit(euc_dist)
    #density = np.exp(kde.score_samples(lcf)).reshape(-1,1)
    kde = KernelDensity(bandwidth=0.9).fit(temp)
    #kde = gaussian_kde(temp)
    density = np.exp(kde.score_samples(temp)).reshape(-1,1)
    factor=1.5
    if min(lcf) < 0: min_lcf=min(lcf) * factor
    elif min(lcf) > 0: min_lcf = min(lcf)  * (1/factor)
    else : min_lcf=-max(lcf)

    if max(lcf) < 0: max_lcf=max(lcf) * (1/factor)
    elif max(lcf) > 0: max_lcf = max(lcf) * factor
    else : max_lcf= -min_lcf

    min_euc_dist =0
    max_euc_dist = max(euc_dist)
    n=len(density)*2
    xlin =np.linspace(min_lcf,max_lcf,n).reshape(-1,1)
    dlin =np.linspace(min_euc_dist,max_euc_dist,n).reshape(-1,1)
    xx,dd = np.meshgrid(xlin, dlin)
    xx=xx.reshape(-1,1)
    dd=dd.reshape(-1,1)
    lin = np.concatenate([xx,dd],axis=1) #.reshape(-1,1)
    #lin = xx
    ddx=(max_lcf-min_lcf)*(max_euc_dist-min_euc_dist)/n**2
    #ddx=(max_lcf-min_lcf)/n
    lin_density=np.exp(kde.score_samples(lin)).reshape(-1,1)
    n=len(density)
    cum_dense=np.zeros(n).reshape(-1,1)
    for l,ed,i in zip(lcf,euc_dist,range(n)):
        cum_dense[i] = np.sum([ lin_density[j] for j in range(len(xx)) if dd[j] < ed ]) * ddx 
    return(cum_dense)

