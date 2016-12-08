import tensorflow as tf
import numpy as np
import numpy as np


batch_size = 100
# Linear model synthetic input
class I:
    def __init__(self, initial_dim, input_size, n_layer, sess):
        # initial_dim: from original input(constant over different layers)

        self.sess = sess
        self.optimizer = tf.train.AdamOptimizer()
        
        self.x_batch = tf.placeholder(tf.float32, shape=(None, initial_dim))
        # self.true_input.shape = (1, num_nodes)
        self.true_input = tf.placeholder(tf.float32, shape=(None, input_size))
        self.initial_dim = initial_dim

        last_inputs = self.x_batch
        # self.syn_input.shape = (1, num_nodes)
        for i in xrange(n_layer):
            last_inputs = tf.contrib.layers.fully_connected(inputs=last_inputs, num_outputs=10)
        self.syn_input = tf.contrib.layers.fully_connected(inputs=last_inputs, num_outputs=input_size)

        # Define loss function
        self.loss = tf.nn.l2_loss(self.true_input-self.syn_input)
        self.train_step = self.optimizer.minimize(self.loss)
        
        self.sess.run(tf.initialize_all_variables())
        
        # a list of batch_size * input_size
        self.x_batch_vals = {}
    
    # h_val.shape = (batch_size, output_size)
    def get_syn_input(self, x_batch_val, ite):
        # Change it to (1, output_size)
        # h_val = np.expand_dims(h_val, axis=0)
        if x_batch_val.shape[0] == batch_size:
            self.x_batch_vals[ite] = x_batch_val

        # Evaluate it, then reshape it to 1D array
        self.syn_input_val = self.syn_input.eval(session=self.sess, feed_dict={self.x_batch:x_batch_val})

        return self.syn_input_val
    
    # true_gradient_val.shape = (num_parameters,)
    def update_model(self, true_input_vals, ite):
        
        if ite in self.x_batch_vals:
            x_batch_val = self.x_batch_vals.pop(ite)
            self.sess.run(self.train_step, feed_dict= {self.true_input:true_input_vals, self.x_batch: x_batch_val})
            # print 'I: ' + str(self.loss.eval(feed_dict={self.true_input:true_input_vals, self.x_batch: x_batch_val}, session=self.sess))
        


