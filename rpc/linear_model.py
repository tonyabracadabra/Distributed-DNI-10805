import tensorflow as tf
import numpy as np

# Linear model synthetic gradient
class linear_model:
    def __init__(self, output_dimension, num_parameters, n_layer):
        # output_dimension: number of nodes in a layer
        # num_parameters: n_weights + n_biases

        self.sess = tf.Session()
        self.optimizer = tf.train.AdamOptimizer()
        
        self.h = tf.placeholder(tf.float32, shape=(1, output_dimension))
        
        # self.true_gradient.shape = (1, num_parameters)
        self.true_gradient = tf.placeholder(tf.float32, shape=(1, num_parameters))

        last_inputs = self.h
        # self.syn_gradient.shape = (1, num_parameters)
        for i in xrange(1-n_layer):
            last_inputs = tf.contrib.layers.fully_connected(inputs=last_inputs, num_outputs=10)
        self.syn_gradient = tf.contrib.layers.fully_connected(inputs=last_inputs, num_outputs=num_parameters)

        # Define loss function
        self.loss = tf.nn.l2_loss(self.true_gradient-self.syn_gradient)
        self.train_step = self.optimizer.minimize(self.loss)
        
        self.sess.run(tf.initialize_all_variables())
        
        self.h_vals = {}
    
    # h_val.shape = (batch_size, output_size)
    def get_syn_gradients(self, h_val, ite):
        # Change it to (1, output_size)
        # h_val = np.expand_dims(h_val, axis=0)
        h_val = h_val.reshape(1,h_val.shape[0])
        self.h_vals[ite] = h_val
        
        # Evaluate it, then reshape it to 1D array
        self.syn_gradient_val =  np.reshape(self.syn_gradient.eval(session=self.sess, \
                                            feed_dict={self.h:h_val}),-1)

        return self.syn_gradient_val
    
    # true_gradient_val.shape = (num_parameters,)
    def update_model(self, true_gradient_val, ite):
        true_gradient_val = np.expand_dims(true_gradient_val,axis=0)
        # print true_gradient_val
        if ite in self.h_vals:
            h_val = self.h_vals.pop(ite)
            h = self.sess.partial_run_setup([self.syn_gradient,self.train_step], [self.h,self.true_gradient])
            syn_gradient_val = self.sess.partial_run(h, self.syn_gradient, feed_dict = {self.h:h_val})
            print "syn: " + str(sum(syn_gradient_val))
            print "true: " + str(sum(true_gradient_val))
            # self.sess.partial_run(h, self.train_step, feed_dict = {self.true_gradient:true_gradient_val})
            self.sess.run(self.train_step, feed_dict= \
                {self.true_gradient: true_gradient_val, self.syn_gradient: syn_gradient_val, self.h:h_val})
            # print 'M: ' + str(self.loss.eval(feed_dict = {self.true_gradient: true_gradient_val, self.h: h_val}, session=self.sess))