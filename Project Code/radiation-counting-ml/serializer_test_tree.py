from functools import partial
import timeit
from typing import Dict, List

import numpy as np
from sklearn.model_selection import cross_val_score
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.ensemble import ExtraTreesClassifier

from lib.ortec_file_utils import get_training_data
from lib.serializer import Serializer


def bin_list(arr: List[int], bin_size: int):
    sp = np.array_split(arr, bin_size)
    sums = [part.sum() for part in sp]
    return sums


labels: List[str] = ['Cs-137', 'Ba-133', 'Co-60']
mlb = MultiLabelBinarizer()
mlb.fit([labels])


def print_proba(results: List[List[int]]):
    print('Probabilities:\n\t' + '\n\t'.join([
        f'{mlb.classes_[idx]}:\t{prob[0]}' for idx, prob in enumerate(results)
    ]))


def print_prediction(results: List[List[int]]):
    print(f'Prediction: {mlb.inverse_transform(results)[0]}')


num_training_lists = 10
print(f'Using {num_training_lists} snapshots from each spectrum')

bin_size = 10
# print(f'Using {bin_size} bins')
bin_train = partial(bin_list, bin_size=bin_size)

sample_files: Dict = {
    'cs.dat': {'labels': ['Cs-137']},
    'ba.dat': {'labels': ['Ba-133']},
    'co.dat': {'labels': ['Co-60']},
    '2020-01-31_co_ba.dat': {'labels': ['Ba-133', 'Co-60']},
    '2020-01-31_cs_ba.dat': {'labels': ['Ba-133', 'Cs-137']},
    '2020-01-31_cs_co.dat': {'labels': ['Co-60', 'Cs-137']},
    'ba_co_cs.dat': {'labels': ['Ba-133', 'Co-60', 'Cs-137']}
}

for key, value in sample_files.items():
    value['data'] = get_training_data("data/" + key, num_training_lists)

# Combine all the training data arrays into one big feature set
X = np.vstack(list(map(lambda x: x['data'], sample_files.values())))
# X = normalize(X)

# Build a label list that corresponds to the feature set
y = []
for value in sample_files.values():
    y += [value['labels']]*len(value['data'])
y = np.array(mlb.transform(y))

# Use a multi-label classifier implementing Multinomial Naive Bayes
clf = MultiOutputClassifier(ExtraTreesClassifier(max_depth=5))
clf.fit(X, y)

print(f'Mean accuracy: {clf.score(X, y)}')

num_folds = 10
cv_score = cross_val_score(clf, X, y, cv=num_folds)
print(f'{num_folds}-fold cross-validation: {cv_score}')

# Perform real-time tests for each input file
for key, value in sample_files.items():
    print("\nPerforming real-time classification of "
          f"{', '.join(value['labels'])}")
    start_time = timeit.default_timer()
    features = Serializer("data/" + key).classify_realtime(
            clf,
            wait_for_min_counts=False,
            classification_interval_counts=1000
    )
    total_time = timeit.default_timer() - start_time
    print(f'Classified in {total_time} seconds')
    print_prediction(clf.predict(features))
    print_proba(clf.predict_proba(features))
