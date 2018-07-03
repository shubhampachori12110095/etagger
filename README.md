etagger
====

### description

- original git repository
  - https://github.com/monikkinom/ner-lstm

- modification
  - modified for tf version(1.6)
  - removed unnecessary files
  - refactoring .... ing

### pre-requisites

- data
  - [download](https://github.com/mxhofer/Named-Entity-Recognition-BidirectionalLSTM-CNN-CoNLL) 
  - place train.txt, dev.txt, test.txt in data dir

- glove embedding
  - [download](http://nlp.stanford.edu/data/glove.6B.zip)
  - unzip to 'embedding' dir

### how to 

- make glove pickle data
```
$ cd embeddings
$ python glove_model.py --dimension 50 --restore glove.6B.50d.txt
```

- convert train/dev/test text file to embedding format
```
$ cd embeddings
$ python get_conll_embeddings.py --train ../data/train.txt --test_a ../data/dev.txt --test_b ../data/test.txt --use_model glovevec_model_50.pkl --model_dim 50 --sentence_length 125

```

- train
```
$ python model.py --word_dim 61 --sentence_length 125 --class_size 5 --rnn_size 256 --num_layers 1 --batch_size 128 --epoch 50
...
116-th batch in 14987(size of train_inp)
117-th batch in 14987(size of train_inp)
epoch 49:
test_a score:
[0.96773173046504268, 0.93732327992459941, 0.88112566715186802, 0.8534119629317608, 0.99481961576881084, 0.92333841284726292]

PER, LOC, ORG, MISC, O
```
