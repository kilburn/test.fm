# -*- coding: utf-8 -*-
"""
Created on 16 January 2014

Connector for the tensor CoFi Java implementation

.. moduleauthor:: joaonrb <joaonrb@gmail.com>
"""
__author__ = {
    'name':'joaonrb',
    'e-mail': 'joaonrb@gmail.com'
}
__version__ = 1, 0, 0
__since__ = 16, 1, 2014

from pkg_resources import resource_filename
import testfm
import os
import numpy as np

os.environ['CLASSPATH'] = resource_filename(testfm.__name__, 'lib/'
    'algorithm-1.0-SNAPSHOT-jar-with-dependencies.jar')

import datetime
import subprocess

from jnius import autoclass
import numpy
import pandas as pd
from testfm.models.interface import ModelInterface
from testfm.config import USER, ITEM

JavaTensorCoFi = autoclass('es.tid.frappe.recsys.TensorCoFi')
FloatMatrix = autoclass('org.jblas.FloatMatrix')
Arrays = autoclass('java.util.Arrays')


class TensorCoFi(ModelInterface):

    def __init__(self, dim=20, nIter=5, lamb=0.05, alph=40,
                 user_features=["user"], item_features=["item"]):
        """
        Python model creator fro tensor implementation in java

        **Args**

            *pandas.DataFrame* trainData:
                The data to train the tensor

            *int* dim:
                Dimension of some kind. Default = 20.

            *int* nIter:
                Nmber of iteration. Default = 5.

            *float* lamb:
                Lambda value for the algorithm. Default = 0,05.

            *int* alph:
                Alpha number for the algorithm. Default = 40.

        """
        self.setParams(dim,nIter, lamb, alph)
        self.user_features = {}
        self.item_features = {}
        self.factors = {}

        self.user_column_names = user_features
        self.item_column_names = item_features

    @classmethod
    def paramDetails(cls):
        """
        Return parameter details for dim, nIter, lamb and alph
        """
        return {
            'dim': (10, 20, 2, 20),
            'nIter': (1, 10, 2, 5),
            'lamb': (.1, 1., .1, .05),
            'alph': (30, 50, 5, 40)
        }

    def _dataframe_to_float_matrix(self, df):
        id_map = {}

        self.user_features = {}  # map from user to indexes
        self.item_features = {}  # map from item to indexes

        features = self.user_column_names + self.item_column_names
        mc = FloatMatrix(len(df), len(features))
        for row_id, row_data in enumerate(df.iterrows()):
            _, tuple_var = row_data
            user_idx = []
            item_idx = []
            for i, c in enumerate(features):
                cmap = id_map.get(c, {})
                value = cmap.get(tuple_var[c], len(cmap)+1)
                cmap[tuple_var[c]] = value
                id_map[c] = cmap
                mc.put(row_id, i, value)
                if c in self.user_column_names:
                    user_idx.append(value)
                if c in self.item_column_names:
                    item_idx.append(value)

            self.user_features[tuple_var['user']] = user_idx
            self.item_features[tuple_var['item']] = item_idx
        return mc, id_map

    def _fit(self,data):
        """
        Return the model
        """
        #data, tmap = self._map(data)
        data, tmap = self._dataframe_to_float_matrix(data)
        self._dmap = tmap

        dims = [len(self._dmap[c])
                for c in self.user_column_names + self.item_column_names]

        tensor = JavaTensorCoFi(self._dim, self._nIter, self._lamb, self._alph,
                                dims)
        tensor.train(data)

        final_model = tensor.getModel()
        self.factors = {}
        for i, c in enumerate(self.user_column_names+self.item_column_names):
            self.factors[c] = self._float_matrix2numpy(
                final_model.get(i)).transpose()
        return tensor

    def fit(self,data):
        """
        Prepare the model
        """
        self._fit(data)

    def _float_matrix2numpy(self, java_float_matrix):
        """
        Java Float Matrix is a 1-D array writen column after column.
        Numpy reads row after row, therefore, we need a conversion.
        """
        columns_input = java_float_matrix.toArray()
        split = lambda lst, sz: [numpy.fromiter(lst[i:i+sz],dtype=numpy.float)
                                 for i in range(0, len(lst), sz)]
        cols = split(columns_input, java_float_matrix.rows)
        matrix = numpy.ma.column_stack(cols)
        return matrix

    def getScore(self, user, item):
        names = self.user_column_names + self.item_column_names
        indexes = self.user_features[user] + self.item_features[item]
        for i, name in enumerate(names):
            try:
                ret = np.multiply(ret, self.factors[name][indexes[i]-1])
            except NameError:
                ret = self.factors[name][indexes[i]-1]
        return sum(ret)

    def setParams(self,dim=20, nIter=5, lamb=0.05, alph=40):
        """
        Set the parameters for the TensorCoFi
        """
        self._dim = dim
        self._nIter = nIter
        self._lamb = lamb
        self._alph = alph

    def getName(self):
        return "TensorCoFi (dim={},iter={},lambda={},alpha={})".format(
            self._dim, self._nIter, self._lamb, self._alph)


class TensorCoFiByFile(TensorCoFi):

    _dmap = {}

    def _map(self,df):
        id_map = {}

        self.user_features = {}  #map from user to indexes
        self.item_features = {}  #map from item to indexes

        features = self.user_column_names + self.item_column_names
        mc = []
        for row_id, row_data in enumerate(df.iterrows()):
            _, tuple_var = row_data
            user_idx = []
            item_idx = []
            t = []
            for i, c in enumerate(features):
                cmap = id_map.get(c, {})
                value = cmap.get(tuple_var[c], len(cmap)+1)
                cmap[tuple_var[c]] = value
                id_map[c] = cmap
                t.append(value)
                if c in self.user_column_names:
                    user_idx.append(value)
                if c in self.item_column_names:
                    item_idx.append(value)
            mc.append(t)
            self.user_features[tuple_var['user']] = user_idx
            self.item_features[tuple_var['item']] = item_idx
        return pd.DataFrame({k:v for k,v in zip(features,zip(*mc))}), id_map

    def fit(self,data):
        data, tmap = self._map(data)
        self._dmap = tmap
        directory = 'log/' + datetime.datetime.now().isoformat('_')
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(directory+'/train.csv','w') as datafile:
            data.to_csv(datafile, header=False, index=False,
                        cols=['user','item'])
            name = os.path.dirname(datafile.name)+'/'
        sub = subprocess.Popen(['java', '-cp' , resource_filename(
            testfm.__name__, 'lib/algorithm-1.0-SNAPSHOT-jar-with-dependencies'
                             '.jar'),
            'es.tid.frappe.python.TensorCoPy', name, str(self._dim),
            str(self._nIter), str(self._lamb), str(self._alph),
            str(len(tmap[USER])), str(len(tmap[ITEM]))],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = sub.communicate()
        if err:
            #os.remove(name)
            print out
            raise Exception(err)
        users, items = out.split(' ')
        self.factors = {
            'user': numpy.ma.column_stack(numpy.genfromtxt(
                open(users,'r'), delimiter=',')),
            'item': numpy.ma.column_stack(numpy.genfromtxt(
                open(items,'r'), delimiter=','))
        }

if __name__ == '__main__':
    t = TensorCoFiByFile()
    t.fit(pd.DataFrame({
        'user': [1, 1, 3, 4], 'item': [1, 2, 3, 4], 'rating': [5,3,2,1],
        'date': [11,12,13,14]}))
    t.getScore(1, 4)
