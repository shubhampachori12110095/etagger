from __future__ import print_function
import tensorflow as tf
import numpy as np
from embvec import EmbVec
from config import Config
from model import Model
from token_eval  import TokenEval
from chunk_eval  import ChunkEval
from viterbi import viterbi_decode
from input import Input
import sys
import time
import argparse

def inference_bulk(config):
    """Inference for test file
    """

    # Build input data
    test_file = 'data/test.txt'
    test_data = Input(test_file, config)
    print('loading input data ... done')

    # Create model
    model = Model(config)

    session_conf = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    sess = tf.Session(config=session_conf)
    with sess.as_default():
        feed_dict = {}
        if not config.use_elmo: feed_dict = {model.wrd_embeddings_init: config.embvec.wrd_embeddings}
        sess.run(tf.global_variables_initializer(), feed_dict=feed_dict)
        saver = tf.train.Saver()
        saver.restore(sess, config.restore)
        print('model restored')
        feed_dict = {model.input_data_pos_ids: test_data.sentence_pos_ids,
                     model.input_data_etcs: test_data.sentence_etcs,
                     model.output_data: test_data.sentence_tags,
                     model.is_train: False,
                     model.sentence_length: test_data.max_sentence_length}
        if config.use_elmo:
            feed_dict[model.elmo_input_data_wordchr_ids] = test_data.sentence_elmo_wordchr_ids
        else:
            feed_dict[model.input_data_word_ids] = test_data.sentence_word_ids
            feed_dict[model.input_data_wordchr_ids] = test_data.sentence_wordchr_ids
        logits, logits_indices, trans_params, output_data_indices, sentence_lengths, test_loss = \
                     sess.run([model.logits, model.logits_indices, model.trans_params, \
                               model.output_data_indices, model.sentence_lengths, model.loss], \
                               feed_dict=feed_dict)
        print('test precision, recall, f1(token): ')
        TokenEval.compute_f1(config.class_size, logits, test_data.sentence_tags, sentence_lengths)
        if config.use_crf:
            viterbi_sequences = viterbi_decode(logits, trans_params, sentence_lengths)
            tag_preds = test_data.logits_indices_to_tags_seq(viterbi_sequences, sentence_lengths)
        else:
            tag_preds = test_data.logits_indices_to_tags_seq(logits_indices, sentence_lengths)
        tag_corrects = test_data.logits_indices_to_tags_seq(output_data_indices, sentence_lengths)
        test_prec, test_rec, test_f1 = ChunkEval.compute_f1(tag_preds, tag_corrects)
        print('test precision, recall, f1(chunk): ', test_prec, test_rec, test_f1)

def inference_bucket(config):
    """Inference for bucket
    """

    # Create model
    model = Model(config)

    # Restore model
    session_conf = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    '''
    session_conf = tf.ConfigProto(allow_soft_placement=True,
                                  log_device_placement=False,
                                  inter_op_parallelism_threads=1,
                                  intra_op_parallelism_threads=1)
    '''
    sess = tf.Session(config=session_conf)
    feed_dict = {}
    if not config.use_elmo: feed_dict = {model.wrd_embeddings_init: config.embvec.wrd_embeddings}
    sess.run(tf.global_variables_initializer(), feed_dict=feed_dict)
    saver = tf.train.Saver()
    saver.restore(sess, config.restore)
    sys.stderr.write('model restored' +'\n')

    num_buckets = 0
    total_duration_time = 0.0
    bucket = []
    while 1:
        try: line = sys.stdin.readline()
        except KeyboardInterrupt: break
        if not line: break
        line = line.strip()
        if not line and len(bucket) >= 1:
            start_time = time.time()
            # Build input data
            inp = Input(bucket, config)
            feed_dict = {model.input_data_pos_ids: inp.sentence_pos_ids,
                         model.input_data_etcs: inp.sentence_etcs,
                         model.output_data: inp.sentence_tags,
                         model.is_train: False,
                         model.sentence_length: inp.max_sentence_length}
            if config.use_elmo:
                feed_dict[model.elmo_input_data_wordchr_ids] = inp.sentence_elmo_wordchr_ids
            else:
                feed_dict[model.input_data_word_ids] = inp.sentence_word_ids
                feed_dict[model.input_data_wordchr_ids] = inp.sentence_wordchr_ids
            logits, trans_params, sentence_lengths, loss = \
                         sess.run([model.logits, model.trans_params, \
                                   model.sentence_lengths, model.loss], \
                                   feed_dict=feed_dict)
            if config.use_crf:
                viterbi_sequences = viterbi_decode(logits, trans_params, sentence_lengths)
                tags = inp.logit_indices_to_tags(viterbi_sequences[0], sentence_lengths[0])
            else:
                tags = inp.logit_to_tags(logits[0], sentence_lengths[0])
            for i in range(len(bucket)):
                out = bucket[i] + ' ' + tags[i]
                sys.stdout.write(out + '\n')
            sys.stdout.write('\n')
            bucket = []
            duration_time = time.time() - start_time
            out = 'duration_time : ' + str(duration_time) + ' sec'
            sys.stderr.write(out + '\n')
            num_buckets += 1
            total_duration_time += duration_time
        if line : bucket.append(line)
    if len(bucket) != 0:
        start_time = time.time()
        # Build input data
        inp = Input(bucket, config)
        feed_dict = {model.input_data_pos_ids: inp.sentence_pos_ids,
                     model.input_data_etcs: inp.sentence_etcs,
                     model.output_data: inp.sentence_tags,
                     model.is_train: False,
                     model.sentence_length: inp.max_sentence_length}
        if config.use_elmo:
            feed_dict[model.elmo_input_data_wordchr_ids] = inp.sentence_elmo_wordchr_ids
        else:
            feed_dict[model.input_data_word_ids] = inp.sentence_word_ids
            feed_dict[model.input_data_wordchr_ids] = inp.sentence_wordchr_ids
        logits, trans_params, sentence_lengths, loss = \
                     sess.run([model.logits, model.trans_params, \
                               model.sentence_lengths, model.loss], \
                               feed_dict=feed_dict)
        if config.use_crf:
            viterbi_sequences = viterbi_decode(logits, trans_params, sentence_lengths)
            tags = inp.logit_indices_to_tags(viterbi_sequences[0], sentence_lengths[0])
        else:
            tags = inp.logit_to_tags(logits[0], sentence_lengths[0])
        for i in range(len(bucket)):
            out = bucket[i] + ' ' + tags[i]
            sys.stdout.write(out + '\n')
        sys.stdout.write('\n')
        duration_time = time.time() - start_time
        out = 'duration_time : ' + str(duration_time) + ' sec'
        sys.stderr.write(out + '\n')
        num_buckets += 1
        total_duration_time += duration_time

    out = 'total_duration_time : ' + str(total_duration_time) + ' sec' + '\n'
    out += 'average processing time / bucket : ' + str(total_duration_time / num_buckets) + ' sec'
    sys.stderr.write(out + '\n')

    sess.close()

def inference_line(config):
    """Inference for raw string
    """
    def get_entity(doc, begin, end):
        for ent in doc.ents:
            # check included
            if ent.start_char <= begin and end <= ent.end_char:
                if ent.start_char == begin: return 'B-' + ent.label_
                else: return 'I-' + ent.label_
        return 'O'
     
    def build_bucket(nlp, line):
        bucket = []
        doc = nlp(line)
        for token in doc:
            begin = token.idx
            end   = begin + len(token.text) - 1
            temp = []
            '''
            print(token.i, token.text, token.lemma_, token.pos_, token.tag_, token.dep_,
                  token.shape_, token.is_alpha, token.is_stop, begin, end)
            '''
            temp.append(token.text)
            temp.append(token.tag_)
            temp.append('O')     # no chunking info
            entity = get_entity(doc, begin, end)
            temp.append(entity)  # entity by spacy
            temp = ' '.join(temp)
            bucket.append(temp)
        return bucket

    import spacy
    nlp = spacy.load('en')

    # Create model
    model = Model(config)

    # Restore model
    session_conf = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    sess = tf.Session(config=session_conf)
    feed_dict = {}
    if not feed_dict: feed_dict = {model.wrd_embeddings_init: config.embvec.wrd_embeddings}
    sess.run(tf.global_variables_initializer(), feed_dict=feed_dict)
    saver = tf.train.Saver()
    saver.restore(sess, config.restore)
    sys.stderr.write('model restored' +'\n')

    while 1:
        try: line = sys.stdin.readline()
        except KeyboardInterrupt: break
        if not line: break
        line = line.strip()
        if not line: continue
        # Create bucket
        try: bucket = build_bucket(nlp, line)
        except Exception as e:
            sys.stderr.write(str(e) +'\n')
            continue
        # Build input data
        inp = Input(bucket, config)
        feed_dict = {model.input_data_pos_ids: inp.sentence_pos_ids,
                     model.input_data_etcs: inp.sentence_etcs,
                     model.output_data: inp.sentence_tags,
                     model.is_train: False,
                     model.sentence_length: inp.max_sentence_length}
        if config.use_elmo:
            feed_dict[model.elmo_input_data_wordchr_ids] = inp.sentence_elmo_wordchr_ids
        else:
            feed_dict[model.input_data_word_ids] = inp.sentence_word_ids
            feed_dict[model.input_data_wordchr_ids] = inp.sentence_wordchr_ids
        logits, trans_params, sentence_lengths, loss = \
                     sess.run([model.logits, model.trans_params, \
                               model.sentence_lengths, model.loss], \
                               feed_dict=feed_dict)
        if config.use_crf:
            viterbi_sequences = viterbi_decode(logits, trans_params, sentence_lengths)
            tags = inp.logit_indices_to_tags(viterbi_sequences[0], sentence_lengths[0])
        else:
            tags = inp.logit_to_tags(logits[0], sentence_lengths[0])
        for i in range(len(bucket)):
            out = bucket[i] + ' ' + tags[i]
            sys.stdout.write(out + '\n')
        sys.stdout.write('\n')

    sess.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emb_path', type=str, help='path to word embedding vector(.pkl)', required=True)
    parser.add_argument('--wrd_dim', type=int, help='dimension of word embedding vector', required=True)
    parser.add_argument('--word_length', type=int, default=15, help='max word length')
    parser.add_argument('--restore', type=str, help='path to saved model(ex, ./checkpoint/model_max.ckpt)', required=True)
    parser.add_argument('--mode', type=str, default='bulk', help='bulk, bucket, line')

    args = parser.parse_args()
    config = Config(args, is_train=False, use_elmo=False, use_crf=True)
    if args.mode == 'bulk':   inference_bulk(config)
    if args.mode == 'bucket': inference_bucket(config)
    if args.mode == 'line':   inference_line(config)
