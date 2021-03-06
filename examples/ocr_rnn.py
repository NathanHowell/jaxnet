# Run this example in your browser: https://colab.research.google.com/drive/1YuI6GUtMgnMiWtqoaPznwAiSCe9hMR1E

from jax import numpy as np, random
from jax.nn import softmax
from jax.random import PRNGKey

from jaxnet import Sequential, Rnn, Dense, GRUCell, parametrized, optimizers


def read_dataset():
    import sets
    dataset = sets.Ocr()
    dataset = sets.OneHot(dataset.target, depth=2)(dataset, columns=['target'])
    dataset['data'] = dataset.data.reshape(dataset.data.shape[:-2] + (-1,)).astype(float)
    return sets.Split(0.66)(dataset)


def main():
    train, test = read_dataset()
    _, length, x_size = train.data.shape
    class_count = train.target.shape[2]
    carry_size = 200
    batch_size = 10

    def rnn():
        return Rnn(*GRUCell(carry_size=carry_size,
                            param_init=lambda key, shape: random.normal(key, shape) * 0.01))

    net = Sequential(
        rnn(),
        rnn(),
        rnn(),
        lambda x: np.reshape(x, (-1, carry_size)),  # -> same weights for all time steps
        Dense(out_dim=class_count),
        softmax,
        lambda x: np.reshape(x, (-1, length, class_count)))

    @parametrized
    def cross_entropy(images, targets):
        prediction = net(images)
        return np.mean(-np.sum(targets * np.log(prediction), (1, 2)))

    @parametrized
    def error(inputs, targets):
        prediction = net(inputs)
        return np.mean(np.not_equal(np.argmax(targets, 2), np.argmax(prediction, 2)))

    opt = optimizers.RmsProp(0.003)

    batch = train.sample(batch_size)
    state = opt.init(cross_entropy.init_parameters(batch.data, batch.target, key=PRNGKey(0)))
    for epoch in range(10):
        params = opt.get_parameters(state)
        e = error.apply_from({cross_entropy: params}, test.data, test.target, jit=True)
        print(f'Epoch {epoch} error {e * 100:.1f}')

        for _ in range(100):
            batch = train.sample(batch_size)
            state = opt.update(cross_entropy.apply, state, batch.data, batch.target, jit=True)


if __name__ == '__main__':
    main()
