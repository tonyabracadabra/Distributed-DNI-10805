import thriftpy
import pickle
import numpy as np
from M import *
linear_thrift = thriftpy.load("linear.thrift", module_name="linear_thrift")

from thriftpy.rpc import make_server


class Dispatcher(object):
    def initialize(self,initList):
        print 'here'
        initList = pickle.loads(initList)
        self.models = []

        for dim in initList:
            self.models.append(LinearModel(dim[0],dim[1],dim[2]))

        print self.models

    def predict(self, h, id):
        id = int(id)
        currModel = self.models[id] # by id
        h_val = pickle.loads(h)
        syn_gradient = currModel.get_syn_gradients(np.mean(h_val,axis = 0))
        return pickle.dumps(syn_gradient, protocol = 0)

    def update(self, trueGrad, id):
        id = int(id)
        currModel = self.models[id]
        trueGrad_val = pickle.loads(trueGrad)
        # print trueGrad_val
        currModel.update_model(trueGrad_val)
        



server = make_server(linear_thrift.LinearModel, Dispatcher(), '127.0.0.1', 6010)
server.serve()
