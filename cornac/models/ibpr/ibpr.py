# -*- coding: utf-8 -*-
"""
@author: Dung D. Le (Andrew) <ddle.2015@smu.edu.sg> 
"""

import numpy as np
import scipy as sp
import random
import torch
from ...utils.util_data import Dataset

"""Firstly, we define a helper function to generate\sample training ordinal triplets:
   Step 1:  
   given rated item i, randomly choose item j and check whether rating of j is missing or lower than i, 
   if not randomly sample another item. 
   each row of the sampled data in the following form:
        [userId itemId_i itemId_j rating_i rating_j]
   for each user u, he/she prefers item i over item j.
   """
def sampleData(X, data):
    X = sp.sparse.csr_matrix(X)
    sampled_data = np.zeros((data.shape[0], 5), dtype=np.int)
    data = data.astype(int)

    for k in range(0, data.shape[0]):
        u = data[k, 0]
        i = data[k, 1]
        ratingi = data[k, 2]
        j = random.randint(0, X.shape[0] - 1)

        while X[u, j] > ratingi:
            j = random.randint(0, X.shape[1] - 1)

        sampled_data[k, :] = [u, i, j, ratingi, X[u, j]]

    return sampled_data


def ibpr(X, data, k, lamda = 0.005, n_epochs=150, learning_rate=0.001,batch_size = 100, init_params=None):

    Data = Dataset(data)

    #Initial user factors
    if init_params['U'] is None:
        U = torch.randn(X.shape[0], k, requires_grad=True)
    else:
        U = init_params['U']
        U = torch.from_numpy(U)

    #Initial item factors
    if init_params['V'] is None:
        V = torch.randn(X.shape[1], k, requires_grad=True)
    else:
        V = init_params['V']
        V = torch.from_numpy(V)
    
    optimizer = torch.optim.Adam([U, V], lr=learning_rate)
    for epoch in range(n_epochs):

        num_steps = int(Data.data.shape[0]/batch_size)

        for i in range(1, num_steps + 1):
            batch_c,_ = Data.next_batch(batch_size)
            sampled_batch = sampleData(X, batch_c)
            
            regU = U[sampled_batch[:, 0], :]
            regI = V[sampled_batch[:, 1], :]
            regJ = V[sampled_batch[:, 2], :]
            
            regU_norm     = regU / regU.norm(dim = 1)[:, None]
            regI_norm     = regI / regI.norm(dim = 1)[:, None] 
            regJ_norm     = regJ / regJ.norm(dim = 1)[:, None] 
            
            Scorei = torch.acos(torch.clamp(regU_norm.mm(regI_norm.t()), -1 + 1e-7, 1 - 1e-7))  
            Scorej = torch.acos(torch.clamp(regU_norm.mm(regJ_norm.t()), -1 + 1e-7, 1 - 1e-7))  

            loss = lamda * (regU.norm().pow(2) + regI.norm().pow(2) + regJ.norm().pow(2)) - torch.log(torch.sigmoid(Scorej - Scorei)).sum()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        print('epoch:',epoch,'loss:', loss)
    
    # since the user's preference is defined by the angular distance, we can normalize the user/item vectors without changing the ranking
    U = torch.nn.functional.normalize(U, p = 2, dim=1)
    V = torch.nn.functional.normalize(V, p = 2, dim=1)
    U = U.data.numpy()
    V = V.data.numpy()

    res = {'U': U, 'V': V}

    return res

