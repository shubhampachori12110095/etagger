from __future__ import print_function
import tensorflow as tf
import numpy as np

'''
source from https://github.com/Kyubyong/transformer/blob/master/modules.py
'''

def multihead_attention(queries, 
                        keys, 
                        num_units=32, 
                        num_heads=4,
                        model_dim=400,
                        dropout_rate=0,
                        is_training=True,
                        causality=False,
                        scope="multihead_attention", 
                        reuse=None):
    """Applies multihead attention.
    
    Args:
      queries: A 3d tensor with shape of [N, T_q, C_q].
      keys: A 3d tensor with shape of [N, T_k, C_k].
      num_units: A scalar. Attention size. (C)
      num_heads: An int. Number of heads. (h)
      model_dim: output model dimension for the last linear projection. (M)
      dropout_rate: A floating point number.
      is_training: Boolean. Controller of mechanism for dropout.
      causality: Boolean. If true, units that reference the future are masked. 
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.
        
    Returns:
      A 3d tensor with shape of (N, T_q, M)  
    """
    with tf.variable_scope(scope, reuse=reuse):
        # Set the fall back option for num_units
        if num_units is None:
            num_units = queries.get_shape().as_list()[-1]
        
        # Linear projections
        Q = tf.layers.dense(queries, num_units, activation=tf.nn.relu) # (N, T_q, C)
        K = tf.layers.dense(keys, num_units, activation=tf.nn.relu) # (N, T_k, C)
        V = tf.layers.dense(keys, num_units, activation=tf.nn.relu) # (N, T_k, C)
        
        # Split and concat
        Q_ = tf.concat(tf.split(Q, num_heads, axis=2), axis=0) # (h*N, T_q, C/h) 
        K_ = tf.concat(tf.split(K, num_heads, axis=2), axis=0) # (h*N, T_k, C/h) 
        V_ = tf.concat(tf.split(V, num_heads, axis=2), axis=0) # (h*N, T_k, C/h) 

        # Multiplication
        outputs = tf.matmul(Q_, tf.transpose(K_, [0, 2, 1])) # (h*N, T_q, T_k)
        
        # Scale
        outputs = outputs / (K_.get_shape().as_list()[-1] ** 0.5)
        
        # Key Masking
        key_masks = tf.sign(tf.abs(tf.reduce_sum(keys, axis=-1))) # (N, T_k)
        key_masks = tf.tile(key_masks, [num_heads, 1]) # (h*N, T_k)
        key_masks = tf.tile(tf.expand_dims(key_masks, 1), [1, tf.shape(queries)[1], 1]) # (h*N, T_q, T_k)
        
        paddings = tf.ones_like(outputs)*(-2**32+1)
        outputs = tf.where(tf.equal(key_masks, 0), paddings, outputs) # (h*N, T_q, T_k)
  
        # Causality = Future blinding
        if causality:
            diag_vals = tf.ones_like(outputs[0, :, :]) # (T_q, T_k)
            tril = tf.contrib.linalg.LinearOperatorTriL(diag_vals).to_dense() # (T_q, T_k)
            masks = tf.tile(tf.expand_dims(tril, 0), [tf.shape(outputs)[0], 1, 1]) # (h*N, T_q, T_k)
   
            paddings = tf.ones_like(masks)*(-2**32+1)
            outputs = tf.where(tf.equal(masks, 0), paddings, outputs) # (h*N, T_q, T_k)
  
        # Activation
        outputs = tf.nn.softmax(outputs) # (h*N, T_q, T_k)
         
        # Query Masking
        query_masks = tf.sign(tf.abs(tf.reduce_sum(queries, axis=-1))) # (N, T_q)
        query_masks = tf.tile(query_masks, [num_heads, 1]) # (h*N, T_q)
        query_masks = tf.tile(tf.expand_dims(query_masks, -1), [1, 1, tf.shape(keys)[1]]) # (h*N, T_q, T_k)
        outputs *= query_masks # broadcasting. (N, T_q, T_k)
          
        # Dropouts
        outputs = tf.layers.dropout(outputs, rate=dropout_rate, training=tf.convert_to_tensor(is_training))
               
        # Weighted sum
        outputs = tf.matmul(outputs, V_) # ( h*N, T_q, C/h)
        
        # Restore shape
        outputs = tf.concat(tf.split(outputs, num_heads, axis=0), axis=2 ) # (N, T_q, C)

        # Linear projection
        outputs = tf.layers.dense(outputs, model_dim, activation=tf.nn.relu) # (N, T_q, M)
              
    return outputs

def feedforward(inputs, 
                num_units=[1600, 400],
                scope="feed-forward", 
                reuse=None):
    '''Point-wise feed forward net.
    
    Args:
      inputs: A 3d tensor with shape of [N, T, C].
      num_units: A list of two integers.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.
        
    Returns:
      A 3d tensor with the same shape and dtype as inputs
    '''
    with tf.variable_scope(scope, reuse=reuse):
        # Inner layer
        params = {"inputs": inputs, "filters": num_units[0], "kernel_size": 1,
                  "activation": tf.nn.relu, "use_bias": True}
        outputs = tf.layers.conv1d(**params)
        
        # Readout layer
        params = {"inputs": outputs, "filters": num_units[1], "kernel_size": 1,
                  "activation": None, "use_bias": True}
        outputs = tf.layers.conv1d(**params)
    
    return outputs

def normalize(inputs, 
              epsilon = 1e-8,
              scope="layer-norm",
              reuse=None):
    """Applies layer normalization.
    
    Args:
      inputs: A tensor with 2 or more dimensions, where the first dimension has
        `batch_size`.
      epsilon: A floating number. A very small number for preventing ZeroDivision Error.
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.
      
    Returns:
      A tensor with the same shape and data dtype as `inputs`.
    """
    with tf.variable_scope(scope, reuse=reuse):
        inputs_shape = inputs.get_shape()
        params_shape = inputs_shape[-1:]
    
        mean, variance = tf.nn.moments(inputs, [-1], keep_dims=True)
        beta= tf.Variable(tf.zeros(params_shape))
        gamma = tf.Variable(tf.ones(params_shape))
        normalized = (inputs - mean) / ( (variance + epsilon) ** (.5) )
        outputs = gamma * normalized + beta
        
    return outputs

def positional_encoding(lengths,
                        maxlen,
                        num_units,
                        zero_pad=True,
                        scale=True,
                        scope="positional_encoding",
                        reuse=None):
    '''Sinusoidal Positional_Encoding.

    Args:
      lengths: The lengths of the inputs to create position embeddings for.
        An int32 tensor of shape `[batch_size]`.
      maxlen: The maximum length of the input sequence to create position
        embeddings for. An int32 tensor.
      num_units: Output dimensionality
      zero_pad: Boolean. If True, all the values of the first row (id = 0) should be constant zero
      scale: Boolean. If True, the output will be multiplied by sqrt num_units(check details from paper)
      scope: Optional scope for `variable_scope`.
      reuse: Boolean, whether to reuse the weights of a previous layer
        by the same name.

    Returns:
      A tensor of shape `[batch_size, maxlen, num_units]` that contains
      embeddings for each position. All elements past `lengths` are zero.
    '''

    N = tf.shape(lengths)[0]
    T = maxlen
    with tf.variable_scope(scope, reuse=reuse):
        position_ind = tf.tile(tf.expand_dims(tf.range(T), 0), [N, 1]) # (batch_size, maxlen)

        # First part of the PE function: sin and cos argument
        position_enc = np.array([
            [pos / np.power(10000, 2.*i/num_units) for i in range(num_units)]
            for pos in range(T)])

        # Second part, apply the cosine to even columns and sin to odds.
        position_enc[:, 0::2] = np.sin(position_enc[:, 0::2])  # dim 2i
        position_enc[:, 1::2] = np.cos(position_enc[:, 1::2])  # dim 2i+1

        # Convert to a tensor
        lookup_table = tf.convert_to_tensor(position_enc, dtype=tf.float32)

        if zero_pad:
            lookup_table = tf.concat((tf.zeros(shape=[1, num_units]),
                                      lookup_table[1:, :]), 0)
        outputs = tf.nn.embedding_lookup(lookup_table, position_ind)

        if scale:
            outputs = outputs * num_units**0.5

        # Mask out positions that are padded
        mask = tf.sequence_mask(lengths=lengths, maxlen=maxlen, dtype=tf.float32)
        outputs = outputs * tf.expand_dims(mask, 2) # broadcasting

        return outputs

'''
2) source from https://github.com/google/seq2seq/blob/master/seq2seq/encoders/pooling_encoder.py
'''

def position_encoding(sentence_size, embedding_size):
    """
    Position Encoding described in section 4.1 of
    End-To-End Memory Networks (https://arxiv.org/abs/1503.08895).

    Args:
      sentence_size: length of the sentence
      embedding_size: dimensionality of the embeddings

    Returns:
      A numpy array of shape [sentence_size, embedding_size] containing
      the fixed position encodings for each sentence position.
    """
    encoding = np.ones((sentence_size, embedding_size), dtype=np.float32)
    ls = sentence_size + 1
    le = embedding_size + 1
    for k in range(1, le):
        for j in range(1, ls):
          encoding[j-1, k-1] = (1.0 - j/float(ls)) - (
              k / float(le)) * (1. - 2. * j/float(ls))
    return encoding

def create_position_embedding(embedding_dim, num_positions, lengths, maxlen):
    """Creates position embeddings.

    Args:
      embedding_dim: Dimensionality of the embeddings. An integer.
      num_positions: The number of positions to be embedded. For example,
        if you have inputs of length up to 100, this should be 100. An integer.
      lengths: The lengths of the inputs to create position embeddings for.
        An int32 tensor of shape `[batch_size]`.
      maxlen: The maximum length of the input sequence to create position
        embeddings for. An int32 tensor.

    Returns:
      A tensor of shape `[batch_size, maxlen, embedding_dim]` that contains
      embeddings for each position. All elements past `lengths` are zero.
    """
    # Create constant position encodings
    position_encodings = tf.constant(
        position_encoding(num_positions, embedding_dim),
        name="position_encoding")

    # Slice to size of current sequence
    pe_slice = position_encodings[:maxlen, :]
    # Replicate encodings for each element in the batch
    batch_size = tf.shape(lengths)[0]
    pe_batch = tf.tile([pe_slice], [batch_size, 1, 1])

    # Mask out positions that are padded
    positions_mask = tf.sequence_mask(
        lengths=lengths, maxlen=maxlen, dtype=tf.float32)
    positions_embed = pe_batch * tf.expand_dims(positions_mask, 2)

    return positions_embed

