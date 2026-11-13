"""Mean absolute error for a forecast holdout. This is not a solver metric."""


def mean_absolute_error(actual: list[float], predicted: list[float]) -> float:
    if not actual or len(actual) != len(predicted):
        raise ValueError("actual and predicted must be the same non-empty length")
    total = sum(abs(left - right) for left, right in zip(actual, predicted, strict=True))
    return total / len(actual)
