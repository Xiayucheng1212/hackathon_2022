# ECBM E4040 Final Project: WSAE-LSTM
# Author: Yifan Liu
# This is a utility function to help you download the dataset and preprocess the data we use for this homework.
# requires several modules: _pickle, tarfile, glob. If you don't have them, search the web on how to install them.
# You are free to change the code as you like.

# import modules
import os
import sys

import numpy as np
import pandas as pd

sys.path.append("../")

from src.models.stacked_auto_encoder import StackedAutoEncoder
from src.models.wavelet import wavelet_transform

# define training period as 24 months, validation as 3 months, and test as 3 months
NUM_TRAIN = 24
NUM_VAL = 3
NUM_TEST = 3

# # define absolute path
FEATURE_DIR = os.path.abspath(os.path.join(os.path.realpath(__file__), "../../../data"))


def min_max_scale(x, x_train):
    """
    Normalize the inputs data to range(0,1) for auto encoder.
    :arg x: inputs to conduct normalization
    :arg x_train: training data for min max calculation
    :return: normalized data
    """
    return (x - x_train.min(axis=0)) / (x_train.max(axis=0) - x_train.min(axis=0))


def generate_features(raw: pd.DataFrame, sheet_name):
    """
    Generate normalizaed, denoised and encoded features using normalization, wavelet transform and stacked auto-
    encoder.
    :arg raw: data frame contains the data
    :arg sheet_name: sheet name correspond to the raw args
    :return: None
    """

    # treat with messy data
    if sheet_name == 'DJIA index Data':
        raw.WVAD = np.where(raw.WVAD < -1e8, -1e8, raw.WVAD)

    if sheet_name == 'Nifty 50 index Data':
        raw.Ntime = raw.Date

    if sheet_name == 'CSI300 Index Data':
        raw.insert(0, 'Ntime', raw.Time)

    # use month to organize data slice
    month_lst = list(set(raw.Ntime // 10000))
    month_lst.sort()
    month_lst = month_lst[:1003]
    print("This is month length: ")
    print(len(month_lst))
    def get_index(keys):
        ind_lst = []
        for key in keys:
            ind_lst.extend(index_dict[key])
        return ind_lst

    index_dict = dict()
    for month in month_lst:
        index_dict[month] = raw[raw.Ntime // 10000 == month].index.to_list()

    save_dir = FEATURE_DIR + f'/interim/{sheet_name}'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    for i in range(0, len(month_lst) - NUM_TRAIN - NUM_VAL - NUM_TEST + 3, 3):
        train_ind = get_index(month_lst[i:i + NUM_TRAIN])
        val_ind = get_index(month_lst[i + NUM_TRAIN:i + NUM_TRAIN + NUM_VAL])
        test_index = get_index(month_lst[i + NUM_TRAIN + NUM_VAL:i + NUM_TRAIN + NUM_VAL + NUM_TEST])

        save_dir = FEATURE_DIR + f'/interim/{sheet_name}/{month_lst[i + NUM_TRAIN + NUM_VAL]}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # save the second column 'closing price' as target for training LSTM and RNN

        x_train = raw.iloc[train_ind, 1:].values.astype(np.float32)
        y_train = raw.iloc[train_ind, 1].values.astype(np.float32)
        x_val = raw.iloc[val_ind, 1:].values.astype(np.float32)
        y_val = raw.iloc[val_ind, 1].values.astype(np.float32)
        x_test = raw.iloc[test_index, 1:].values.astype(np.float32)
        y_test = raw.iloc[test_index, 1].values.astype(np.float32)
        print("This is train raw data")
        print(x_train.shape, y_train.shape)
        # inputs normalization

        x_train_n = min_max_scale(x_train, x_train)
        y_train_n = min_max_scale(y_train, y_train)
        x_val_n = min_max_scale(x_val, x_train)
        y_val_n = min_max_scale(y_val, y_train)
        x_test_n = min_max_scale(x_test, x_train)
        y_test_n = min_max_scale(y_test, y_train)

        # save normalized data to ./data/interim
        np.save(file=save_dir + '/X_train.npy', arr=x_train_n)
        np.save(file=save_dir + '/Y_train.npy', arr=y_train_n)
        np.save(file=save_dir + '/X_val.npy', arr=x_val_n)
        np.save(file=save_dir + '/Y_val.npy', arr=y_val_n)
        np.save(file=save_dir + '/X_test.npy', arr=x_test_n)
        np.save(file=save_dir + '/Y_test.npy', arr=y_test_n)

        # wavelet transformation
        x_train_nw = wavelet_transform(wavelet_transform(x_train_n))
        x_val_nw = wavelet_transform(wavelet_transform(x_val_n))
        x_test_nw = wavelet_transform(wavelet_transform(x_test_n))

        # save smoothed data to ./data/processed/wavelet
        save_dir = FEATURE_DIR + f'/processed/wavelet/{sheet_name}/{month_lst[i + NUM_TRAIN + NUM_VAL]}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        np.save(file=save_dir + '/X_train.npy', arr=x_train_nw)
        np.save(file=save_dir + '/Y_train.npy', arr=y_train_n)
        np.save(file=save_dir + '/X_val.npy', arr=x_val_nw)
        np.save(file=save_dir + '/Y_val.npy', arr=y_val_n)
        np.save(file=save_dir + '/X_test.npy', arr=x_test_nw)
        np.save(file=save_dir + '/Y_test.npy', arr=y_test_n)

        sae = StackedAutoEncoder(layers=4,
                                 original_dim=x_train_n.shape[1],
                                 intermidiate_dim=10)
        sae.train_stacked_ae(inputs=x_train_n,
                             learning_rate=0.01,
                             n_epochs=20)

        x_train_ne = sae.encode(x_train_n)
        x_val_ne = sae.encode(x_val_n)
        x_test_ne = sae.encode(x_test_n)

        save_dir = FEATURE_DIR + f'/processed/sae/{sheet_name}/{month_lst[i + NUM_TRAIN + NUM_VAL]}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        np.save(file=save_dir + '/X_train.npy', arr=x_train_ne)
        np.save(file=save_dir + '/Y_train.npy', arr=y_train_n)
        np.save(file=save_dir + '/X_val.npy', arr=x_val_ne)
        np.save(file=save_dir + '/Y_val.npy', arr=y_val_n)
        np.save(file=save_dir + '/X_test.npy', arr=x_test_ne)
        np.save(file=save_dir + '/Y_test.npy', arr=y_test_n)

        # train stacked autoencoder
        sae = StackedAutoEncoder(layers=4,
                                 original_dim=x_train_nw.shape[1],
                                 intermidiate_dim=10)
        sae.train_stacked_ae(inputs=x_train_nw,
                             learning_rate=0.01,
                             n_epochs=20)

        x_train_nwe = sae.encode(x_train_nw)
        x_val_nwe = sae.encode(x_val_nw)
        x_test_nwe = sae.encode(x_test_nw)

        save_dir = FEATURE_DIR + f'/processed/wsae/{sheet_name}/{month_lst[i + NUM_TRAIN + NUM_VAL]}'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        np.save(file=save_dir + '/X_train.npy', arr=x_train_nwe)
        np.save(file=save_dir + '/Y_train.npy', arr=y_train_n)
        np.save(file=save_dir + '/X_val.npy', arr=x_val_nwe)
        np.save(file=save_dir + '/Y_val.npy', arr=y_val_n)
        np.save(file=save_dir + '/X_test.npy', arr=x_test_nwe)
        np.save(file=save_dir + '/Y_test.npy', arr=y_test_n)
        print(f">>>>{month_lst[i + NUM_TRAIN + NUM_VAL]} finished!<<<<")

    print(">>>> Feature generation complete! <<<<")
