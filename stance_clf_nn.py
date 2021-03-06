splitterimport json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pushlib_utils import get_subs
def warn(*args, **kwargs):
    pass
import warnings
warnings.warn = warn
from sklearn.feature_extraction import DictVectorizer
from custom_transformers import DictFilterer, exclude_u_sub
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelBinarizer
from sklearn.model_selection import StratifiedShuffleSplit, cross_val_predict, GridSearchCV
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.base import BaseEstimator, TransformerMixin

from tensorflow import keras

import joblib


"""
TODO
find best model:
best sofar: LinearSVC(C=100, loss='hinge', random_state=42)--
best sofar: RandomForestClassifier(min_samples_leaf=3, random_state=42)--
best sofar: VotingClassifier()--

make webapp backend to predict leaning given username
"""
with open('user_profiles.json') as f:
    mldata = json.load(f)

for user, data in mldata.items():
    if mldata[user]['stance'] in ['libright2', 'libright', 'right', 'authright']:
        mldata[user]['stance'] = 'R'
    if mldata[user]['stance'] in ['libleft', 'left', 'authleft']:
        mldata[user]['stance'] = 'L'

# if data['stance'] != 'None'
conditions = lambda user, data: data['stance'] in ['L', 'R'] and user != '[deleted]'
mldata = {user: data for user, data in mldata.items() if conditions(user, data)}

users = [user for user in mldata]
features = [data['subs'] for _, data in mldata.items()]
labels = [data['stance'] for _, data in mldata.items()]
stances = list(set(labels))


full_pipeline = Pipeline([('filterer', DictFilterer(exclude_u_sub)), #k in rel_subs
                            ('vectorizer', DictVectorizer(sparse=True)),
                            ('selectKBest', SelectKBest(chi2, k=1000)),
                            ('scaler', StandardScaler(with_mean=False))])

X = full_pipeline.fit_transform(features, labels).todense()
y = LabelBinarizer().fit_transform(labels).flatten()

print(y)
print(X.shape)


splitter = StratifiedShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
for train_index, test_index in splitter.split(X, y):
    X_train, y_train = X[train_index], y[train_index]
    X_test, y_test = X[test_index], y[test_index]

model = keras.models.Sequential([
                            keras.layers.Dense(30, activation='relu'),
                            keras.layers.Dense(10, activation='relu'),
                            keras.layers.Dense(1, activation='sigmoid')
                                ])
model.compile(loss='binary_crossentropy',
            optimizer='sgd',
            metrics=['accuracy'])

history = model.fit(X_train, y_train, epochs=50, validation_split=0.1)


y_pred = model.predict_classes(X_test).flatten()
print(y_test, y_pred)
conf_mx = confusion_matrix(y_test, y_pred, labels=[0,1])

print(stances)
print(conf_mx)
print('Precision: ', precision_score(y_test, y_pred, average='weighted'))
print('Recall: ', recall_score(y_test, y_pred, average='weighted'))


pd.DataFrame(history.history).plot()
plt.gca().set_ylim(0,1)

fig, ax = plt.subplots()
cax = ax.matshow(conf_mx, cmap=plt.cm.gray)
fig.colorbar(cax)

ax.set_xticks(list(range(len(stances))))
ax.set_yticks(list(range(len(stances))))
ax.set_xticklabels(stances, rotation=45)
ax.set_yticklabels(stances)


xleft, xright = ax.get_xlim()
ybottom, ytop = ax.get_ylim()
ax.set_aspect(abs((xright-xleft)/(ybottom-ytop)))

plt.show()

joblib.dump(full_pipeline, 'models/pipeline_nn.pkl')
joblib.dump(model, 'models/clf_nn.pkl')

def pred_lean(names):
    if type(names) == str: names = [names]
    dict = [get_subs(name) for name in names]
    inst = full_pipeline.transform(dict).todense()
    return model.predict_classes(inst)

#print(pred_lean(['tigeer']))
