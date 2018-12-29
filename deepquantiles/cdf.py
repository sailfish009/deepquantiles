from sklearn.base import BaseEstimator

from keras.models import Model
from keras.layers import Input, Dense, Concatenate
from keras.optimizers import Adam

from .losses import QuantileLossLayer
from .batches import XYQZBatchGenerator


class CDFRegressor(BaseEstimator):

    def __init__(
        self,
        hidden_units=(8, 8),
        activation='relu',
        lr=0.001,
        epochs=10,
        batch_size=100,
        q_mode='const',
        shuffle_points=True
    ):
        self._model_instance = None
        self.hidden_units = hidden_units
        self.activation = activation
        self.lr = lr
        self.epochs = epochs
        self.batch_size = batch_size
        if q_mode not in XYQZBatchGenerator.valid_q_modes:
            raise ValueError(
                f'q_mode must be one of {XYQZBatchGenerator.valid_q_modes}'
            )
        self.q_mode = q_mode
        self.shuffle_points = shuffle_points

    def _model(self):
        input_features = Input(
            (1, ), name='x'
        )
        input_quantile = Input(
            (1, ), name='q'
        )
        input_label = Input(
            (1, ), name='y'
        )
        intermediate = Concatenate()([input_features, input_quantile])
        for idx, units in enumerate(self.hidden_units):
            intermediate = Dense(
                units=units,
                activation=self.activation,
                name=f'dense_{idx}'
            )(intermediate)
        prediction_output = Dense(
            1, name='prediction'
        )(intermediate)

        quantile_model = Model(
            [input_features, input_quantile],
            prediction_output,
            name='Quantile model'
        )

        loss_output = QuantileLossLayer(
            [input_quantile, input_label, prediction_output]
        )

        loss_model = Model(
            [input_features, input_label, input_quantile],
            loss_output,
            name='Loss model'
        )

        loss_model.compile(
            optimizer=Adam(lr=self.lr),
            loss='mean_absolute_error'
        )

        return {
            'loss': loss_model,
            'quantile': quantile_model
        }

    def _init_model(self):
        self._model_instance = self._model()
        return self._model_instance

    @property
    def model(self):
        return self._model_instance or self._init_model()

    def fit(self, X, y, **kwargs):
        self._init_model()
        fit_kwargs = dict(
            epochs=self.epochs,
            batch_size=self.batch_size,
            q_mode=self.q_mode,
            shuffle_points=self.shuffle_points
        )
        fit_kwargs.update(kwargs)

        batch_size = fit_kwargs.pop('batch_size')
        q_mode = fit_kwargs.pop('q_mode')
        shuffle_points = fit_kwargs.pop('shuffle_points')
        gen = XYQZBatchGenerator(
            X, y,
            batch_size=batch_size,
            q_mode=q_mode,
            shuffle_points=shuffle_points
        )

        self.model['loss'].fit_generator(
            gen,
            **fit_kwargs
        )

    def predict(self, X, q):
        return self.model['quantile'].predict([X, q])

    def sample(self, X, num_samples=10, num_quantiles=5):
        quantiles = np.linspace(0, 1, num=num_quantiles)
        pass