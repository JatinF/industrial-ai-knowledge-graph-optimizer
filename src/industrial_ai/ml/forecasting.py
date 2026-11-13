"""Ordinary least squares on a short synthetic series. Integer time index."""


def linear_forecast(values: list[float]) -> float:
    count = len(values)
    if count < 2:
        raise ValueError("forecast needs two points")
    xs = list(range(count))
    mean_x = sum(xs) / count
    mean_y = sum(values) / count
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values, strict=True))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return intercept + slope * count


def advisory_forecast() -> float:
    return linear_forecast([10.0, 12.0, 14.0, 16.0])
