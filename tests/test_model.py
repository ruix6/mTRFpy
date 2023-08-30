from pathlib import Path
import tempfile
import numpy as np
from numpy.random import randint
from mtrf.model import TRF, load_sample_data

n = np.random.randint(3, 10)
stimulus, response, fs = load_sample_data(n_segments=n)


def test_loss_function():
    def mean_absolute_deviation(y, y_pred):
        return np.abs(y - y_pred).mean()

    def mean_difference(y, y_pred):
        return np.mean(y - y_pred)

    for loss_function in [mean_absolute_deviation, mean_difference]:
        trf = TRF(loss_function=loss_function)
        regularization = [
            np.random.uniform(0, 1000) for _ in range(np.random.randint(2, 5))
        ]
        tmin = np.random.uniform(-0.1, 0.05)
        tmax = np.random.uniform(0.1, 0.4)
        loss = trf.train(stimulus, response, fs, tmin, tmax, regularization)
        assert trf.regularization == regularization[np.argmin(loss)]


def test_train():
    tmin = np.random.uniform(-0.1, 0.05)
    tmax = np.random.uniform(0.1, 0.4)
    regularization = np.random.uniform(0, 10)
    for direction in [1, -1]:
        trf = TRF(direction=direction)
        trf.train(stimulus, response, fs, tmin, tmax, regularization)
        if direction == 1:
            assert trf.weights.shape[0] == stimulus[0].shape[-1]
            assert trf.weights.shape[-1] == response[0].shape[-1]
        if direction == -1:
            assert trf.weights.shape[-1] == stimulus[0].shape[-1]
            assert trf.weights.shape[0] == response[0].shape[-1]


def test_optimize():
    for direction in [1, -1]:
        tmin = np.random.uniform(-0.1, 0.05)
        tmax = np.random.uniform(0.1, 0.4)
        trf = TRF(direction=direction)
        regularization = [np.random.uniform(0, 10) for _ in range(randint(2, 5))]
        loss = trf.train(stimulus, response, fs, tmin, tmax, regularization)
    assert len(loss) == len(regularization)


def test_predict():
    tmin = np.random.uniform(-0.1, 0.05)
    tmax = np.random.uniform(0.1, 0.4)
    regularization = np.random.uniform(0, 10)
    trf = TRF()
    trf.train(stimulus, response, fs, tmin, tmax, regularization)
    for average in [True, list(range(randint(response[0].shape[-1])))]:
        prediction, loss = trf.predict(stimulus, response, average=average)
        assert len(prediction) == len(response)
        assert all([p[0].shape == r[0].shape for p, r in zip(prediction, response)])
        assert np.isscalar(loss)
    prediction, loss = trf.predict(stimulus, response, average=False)
    assert loss.shape[-1] == trf.weights.shape[-1]
    trf = TRF(direction=-1)
    trf.train(stimulus, response, fs, tmin, tmax, regularization)
    for average in [True, list(range(randint(stimulus[0].shape[-1])))]:
        prediction, loss = trf.predict(stimulus, response, average=average)
        assert len(prediction) == len(stimulus)
        assert all([p[0].shape == s[0].shape for p, s in zip(prediction, stimulus)])
        assert np.isscalar(loss)
    prediction, r, mse = trf.predict(stimulus, response, average=False)
    assert loss.shape[-1] == trf.weights.shape[-1]


def test_test():
    tmin = np.random.uniform(-0.1, 0.05)
    tmax = np.random.uniform(0.1, 0.4)
    reg = [np.random.uniform(0, 10) for _ in range(randint(2, 10))]
    trf = TRF()
    loss, best_regularization = trf.test(stimulus, response, fs, tmin, tmax, reg)
    assert len(loss) == len(best_regularization) == n


def test_save_load():
    tmpdir = Path(tempfile.gettempdir())
    tmin = np.random.uniform(-0.1, 0.05)
    tmax = np.random.uniform(0.1, 0.4)
    direction = np.random.choice([1, -1])
    regularization = np.random.uniform(0, 10)
    trf1 = TRF(direction=direction)
    trf1.train(stimulus, response, fs, tmin, tmax, regularization)
    trf1.save(tmpdir / "test.trf")
    trf2 = TRF()
    trf2.load(tmpdir / "test.trf")
    np.testing.assert_equal(trf1.weights, trf2.weights)


def test_no_preload(decimal=10):
    for direction in [1, -1]:
        tmin = np.random.uniform(-0.1, 0.05)
        tmax = np.random.uniform(0.1, 0.2)
        regularization = [np.random.uniform(0, 10) for _ in range(2)]
        stimulus, response, fs = load_sample_data(n_segments=4)
        # testing forward model
        trf1 = TRF()
        trf1.train(stimulus, response, fs, tmin, tmax, regularization)
        prediction1, loss1 = trf1.predict(stimulus, response, average=False)
        trf2 = TRF(preload=False)
        trf2.train(stimulus, response, fs, tmin, tmax, regularization)
        prediction2, loss2 = trf2.predict(stimulus, response, average=False)
        # assert all close
        np.testing.assert_almost_equal(trf1.weights, trf2.weights, decimal=decimal)
        np.testing.assert_almost_equal(trf1.bias, trf2.bias, decimal=decimal)
        for pred1, pred2 in zip(prediction1, prediction2):
            np.testing.assert_almost_equal(pred1, pred2, decimal=decimal)
        np.testing.assert_almost_equal(loss1, loss2, decimal=decimal)
