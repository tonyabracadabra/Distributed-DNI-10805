import math
import numpy as np
import tensorflow as tf
from tensorflow.examples.tutorials.mnist import input_data
import pickle
import sys
from M import *
from I import *
from http_interface import *
import base64

reload(sys)
sys.setdefaultencoding('utf-8')

tf.app.flags.DEFINE_integer("input_dimension", int(sys.argv[1]),
                            "Input dimension of this layer")
tf.app.flags.DEFINE_integer("output_dimension", int(sys.argv[2]),
                            "Number of units in this layer")
tf.app.flags.DEFINE_integer("n_layer", int(sys.argv[3]),
                            "Number of layer starts from 1")
tf.app.flags.DEFINE_integer("n_layer_total", int(sys.argv[4]),
                            "Number of all layers")
tf.app.flags.DEFINE_integer("n_classes", int(sys.argv[5]),
                            "Number of classes, used only under the final layer")
tf.app.flags.DEFINE_string("data_dir", "/tmp/mnist-data",
                           "Directory for storing mnist data")

tf.app.flags.DEFINE_integer("batch_size", 100, "Training batch size")
tf.app.flags.DEFINE_float("alpha", 1e-2, "learning rate")

FLAGS = tf.app.flags.FLAGS


n_layer = FLAGS.n_layer
n_layer_total = FLAGS.n_layer_total
n_classes = FLAGS.n_classes
batch_size = FLAGS.batch_size

input_dimension = FLAGS.input_dimension + 1
if n_layer != n_layer_total:
    output_dimension = FLAGS.output_dimension + 1
else:
    output_dimension = FLAGS.output_dimension

IMAGE_PIXELS = 28


def get_shape(variable):
    return tuple([d.value for d in variable.get_shape()])

def append_ones(batch_xs):
    shape = batch_xs.shape
    new_batch_xs = np.ones((shape[0], shape[1] + 1))
    new_batch_xs[:,1:] = batch_xs
    return new_batch_xs


#input data
syn_input = tf.placeholder(tf.float32, [None, input_dimension])

# Define layer parameters

w = tf.Variable(tf.truncated_normal([input_dimension, output_dimension], 
                    stddev=1.0 / (FLAGS.input_dimension * FLAGS.input_dimension)), name="weights")

# Define placeholders for synthetic graident of weights and biases
syn_grad_w = tf.placeholder(tf.float32,[input_dimension, output_dimension])

# If this is the final layer
if n_layer == n_layer_total:
    y_ = tf.placeholder(tf.float32, [None, FLAGS.n_classes])
    y = tf.nn.softmax(tf.matmul(syn_input,w))
    ########################
    # Loss here ...
    layer_output = -tf.reduce_mean(y_ * tf.log(tf.clip_by_value(y, 1e-10, 1.0)))
    ########################
    correct_prediction = tf.equal(tf.argmax(y,1), tf.argmax(y_,1))
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
else:
    layer_output = tf.nn.relu(tf.matmul(syn_input, w))

# Define the gradient from output to w and b
grad_w = tf.gradients(layer_output, w)[0]

# Define gradient to be passed to the previous layer
# Check back later **********************************
grad_succ = tf.placeholder(tf.float32, [None, output_dimension])
grad_curr = tf.gradients(layer_output, syn_input)[0]
true_grad = tf.matmul(tf.transpose(grad_curr),grad_succ)


# Define parameter update operation
update_w = w.assign(w - FLAGS.alpha * syn_grad_w)

# Define the gradient accumulation operation, the true gradient of the previous layer 
# is the product of the true gradient from the following layer to and the gradient
# calculated at this level

# Start session of the layer

num_parameters = input_dimension * output_dimension

mnist = input_data.read_data_sets(FLAGS.data_dir, one_hot=True)

def calc_gpu_fraction(fraction_string):
    idx, num = fraction_string.split('/')
    idx, num = float(idx), float(num)

    fraction = 1 / (num - idx + 1)
    print "[*] GPU : %.4f" % fraction
    return fraction

config = tf.ConfigProto()
config.gpu_options.per_process_gpu_memory_fraction = calc_gpu_fraction('1/4')   
config.gpu_options.allow_growth = True

with tf.Session(config=config) as sess:
    # Instantiate simulators for synthetic gradient and synthetic input
    gradient_simulator = M(output_dimension, num_parameters, n_layer, sess)
    input_simulator = I(IMAGE_PIXELS * IMAGE_PIXELS, input_dimension, n_layer, sess)

    iteration = 0
    while iteration < 20000:
        iteration += 1
        

        batch_xs, batch_ys = mnist.train.next_batch(FLAGS.batch_size)

        if n_layer != 1:
            syn_input_val = input_simulator.get_syn_input(batch_xs,iteration)
        else:
            syn_input_val = batch_xs.astype(np.float32)
            syn_input_val = append_ones(syn_input_val)


        if n_layer != n_layer_total:
            layer_output_val = layer_output.eval(feed_dict={syn_input:syn_input_val})
        else:
            layer_output_val = layer_output.eval(feed_dict={syn_input:syn_input_val,y_:batch_ys})

        ###########################
        # HTTP REQUEST send true input/the output of this layer
        if n_layer != n_layer_total:
            layer_output_val_ser = base64.b64encode(layer_output_val)
            insert_true_input(n_layer, iteration, layer_output_val_ser)
        ###########################

            # Get the synthetic gradient of the model, which contains the update of
            # the weights and the biases
            syn_gradient = gradient_simulator.get_syn_gradients(np.mean(layer_output_val,axis = 0),iteration)
            # Update weights
            sess.run(update_w, feed_dict={syn_grad_w:syn_gradient.reshape(get_shape(w))})

            curr_w_grad_val = grad_w.eval(feed_dict={syn_input:syn_input_val})

        else:
            # Update weights
            sess.run(update_w, feed_dict={syn_grad_w:grad_w.eval(feed_dict={y_:batch_ys,syn_input:syn_input_val})})
        
        
        # After the weights and biases are updated, together with the true gradient at this level
        # and the synthetic_gradient from the succeceding layer, send the "true" gradient to
        # the previous layer

        ###########################
        # HTTP REQUEST, send true gradient
        if n_layer != 1:
            feed_dict = {syn_input:syn_input_val} if n_layer != n_layer_total else {syn_input:syn_input_val,y_:batch_ys}
            grad_curr_val = grad_curr.eval(feed_dict=feed_dict)
            grad_curr_val_ser= base64.b64encode(grad_curr_val)

            # print str(n_layer) + "\t" + str(iteration) + "\t" + grad_curr_val_ser
            insert_true_gradient(n_layer, iteration, grad_curr_val_ser)

        ###########################
        ###########################
        # HTTP REQUEST, get true input to update I model
        if n_layer != 1:
            tmp = get_true_input(n_layer)
            true_input = tmp[0]
            ite = tmp[1]
            if len(true_input) != 0:
                # print 'get true input length: ' + str(len(true_input))
                r = base64.decodestring(true_input)
                true_input = np.frombuffer(r, dtype=np.float32).reshape((batch_size, get_shape(syn_input)[1]))
                input_simulator.update_model(true_input,int(ite))

        ###########################
        ###########################
        # HTTP REQUEST, get true gradient to update M model
        if n_layer != n_layer_total:
            # After getting the true gradient, it is not actually the gradient that can be used to updata
            # the parameters, the gradient for update M is the product 2 variables as defined in true_grad
            tmp = get_true_gradient(n_layer)
            grad_succ_val = tmp[0]
            ite = tmp[1]
            if len(grad_succ_val) != 0:
                r = base64.decodestring(grad_succ_val)
                grad_succ_val = np.frombuffer(r, dtype=np.float32).reshape((batch_size, get_shape(grad_succ)[1]))
                true_grad_val = true_grad.eval(feed_dict={syn_input:syn_input_val,grad_succ:grad_succ_val})
                true_grad_val = true_grad_val.reshape(-1)
                gradient_simulator.update_model(true_grad_val,int(ite))
        ###########################

        if iteration % 100 == 0 and n_layer == n_layer_total:

            if n_layer != 1:
                test_xs = input_simulator.get_syn_input(mnist.test.images,iteration)
                train_xs = input_simulator.get_syn_input(batch_xs,iteration)

            else:
                append_ones(mnist.test.images)
                append_ones(batch_xs)
            print sum(w.eval())
            print str(n_layer) + "\t" + str(iteration)
            print ("Test Loss: %2.2f" % sess.run(layer_output, feed_dict={syn_input:test_xs, y_: mnist.test.labels}))
            # print("Train-Accuracy: %2.2f" % sess.run(accuracy, feed_dict={syn_input:train_xs, y_: batch_ys}))
            # print("Test-Accuracy: %2.2f" % sess.run(accuracy, feed_dict={syn_input:test_xs, y_: mnist.test.labels}))

