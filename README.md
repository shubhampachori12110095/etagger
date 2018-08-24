etagger
====

### description

- named entity tagger using multi-layer Bidirectional LSTM

- original git repository
  - https://github.com/monikkinom/ner-lstm

- modification
  - modified for tf version(1.4)
  - removed unnecessary files
  - fixed bugs for MultiRNNCell()
  - refactoring .... ing
    - implement input.py, config.py [done]
    - split model.py to model.py, train.py, inference.py [done]
      - inference bulk [done]
      - inference bucket [done]
      - inference line using spacy [done]
    - extend 5 class to 9 class [done]
    - apply dropout for train() only [done]
    - apply embedding_lookup()
      - word embedding [done]
        - total fscore : 0.887144259078 (50 epoch, glove50d)
    - apply character-level embedding
      - character embedding [done]
        - total fscore : 0.886939451567 (50 epoch, glove50d, chr_dim=20)
        - total fscore : 0.889747837291 (50 epoch, glove100d, chr_dim=64)
        - total fscore : 0.868482110148 (50 epoch, glove300d, chr_dim=64)
        - total fscore : 0.89127483648  (50 epoch, glove300d, chr_dim=96) <-- best
        - total fscore : 0.88627981313  (50 epoch, glove300d, chr_dim=128)
        - total fscore : 0.889806992662 (150 epoch, glove300d, chr_dim=96)
    - extend linguistic features [undo]
      - check if last character is capital
        - total fscore : 0.886075949367 (50 epoch, glove300d, chr_dim=96)
    - apply gazetter features
    - apply self-attention
    - apply ELMO embedding
    - serve api
- references
  - https://web.stanford.edu/class/cs224n/reports/6896582.pdf
  - http://www.wildml.com/2015/12/implementing-a-cnn-for-text-classification-in-tensorflow/
  - https://github.com/cuteboydot/Sentence-Classification-using-Char-CNN-and-RNN
  - https://github.com/DongjunLee/transformer-tensorflow/blob/master/transformer/attention.py

### pre-requisites

- data
  - [download](https://github.com/mxhofer/Named-Entity-Recognition-BidirectionalLSTM-CNN-CoNLL/tree/master/data) 
  - place train.txt, dev.txt, test.txt in data dir

- glove embedding
  - [download](http://nlp.stanford.edu/data/glove.6B.zip)
  - unzip to 'embeddings' dir

- spacy [optional]
  - if you want to analyze input string and see how it detects entities, then you need to install spacy lib.
  ```
  $ pip install spacy
  $ python -m spacy download en
  ```

### how to 

- convert word embedding to pickle
```
$ python embvec.py --emb_path embeddings/glove.6B.50d.txt --wrd_dim 50 --train_path data/train.txt
$ python embvec.py --emb_path embeddings/glove.6B.100d.txt --wrd_dim 100 --train_path data/train.txt
$ python embvec.py --emb_path embeddings/glove.6B.300d.txt --wrd_dim 300 --train_path data/train.txt
```

- check max sentence length
```
$ python check_sentence_length.py
train, max_sentence_length = 113
dev, max_sentence_length = 109
test, max_sentence_length = 124

* set 125 to sentence_length
```

- train
```
$ python train.py --emb_path embeddings/glove.6B.300d.txt.pkl --wrd_dim 300 --sentence_length 125 --class_size 9
```

- inference(bulk)
```
$ python inference.py --emb_path embeddings/glove.6B.300d.txt.pkl --wrd_dim 300 --sentence_length 125 --class_size 9 --restore checkpoint/model_max.ckpt
```

- inference(bucket)
```
$ python inference.py --mode bucket --emb_path embeddings/glove.6B.300d.txt.pkl --wrd_dim 300 --sentence_length 125 --class_size 9 --restore checkpoint/model_max.ckpt < data/test.txt > pred.txt
$ python eval.py < pred.txt
```

- inference(line)
```
$ python inference.py --mode line --emb_path embeddings/glove.6B.300d.txt.pkl --wrd_dim 300 --sentence_length 125 --class_size 9 --restore checkpoint/model_max.ckpt
...
Obama left office in January 2017 with a 60% approval rating and currently resides in Washington, D.C.
Obama NNP O O B-PER
left VBD O O O
office NN O O O
in IN O O O
January NNP O B-DATE O
2017 CD O I-DATE O
with IN O O O
a DT O O O
60 CD O B-PERCENT O
% NN O I-PERCENT O
approval NN O O O
rating NN O O O
and CC O O O
currently RB O O O
resides VBZ O O O
in IN O O O
Washington NNP O B-GPE B-LOC
, , O I-GPE O
D.C. NNP O B-GPE I-LOC

The Beatles were an English rock band formed in Liverpool in 1960.
The DT O O O
Beatles NNPS O B-PERSON O
were VBD O O O
an DT O O O
English JJ O B-LANGUAGE B-MISC
rock NN O O O
band NN O O O
formed VBN O O O
in IN O O O
Liverpool NNP O B-GPE B-ORG
in IN O O O
1960 CD O B-DATE O
. . O I-DATE O
```

### etc

- analysis
```
f-score (dev)
  B-PER, I-PER, B-LOC, I-LOC, B-ORG, I-ORG, B-MISC, I-MISC, O
  0.94833648904517176, 0.95342673229837183, 0.94333424582534897, 0.87739463601532586, 0.86836363636363634, 0.84922244759972954, 0.83786848072562348, 0.7643504531722054, 0.99355724054519234
  weak points : B-ORG, I-ORG, B-MISC, I-MISC
```
