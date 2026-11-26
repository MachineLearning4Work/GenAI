#!/usr/bin/env python3
"""A tiny, dependency-free ML job for the Terraform/Terragrunt demo."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import List, Tuple


def read_rows(path: Path) -> List[Tuple[float, float]]:
    # The CSV contains one feature (house size) and one target (price).
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = [(float(row["size_sqft"]), float(row["price_k"]),) for row in reader]
    if len(rows) < 2:
        raise ValueError("The data set must contain at least two rows.")
    return rows


def fit_linear_regression(rows: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Fit y = slope*x + intercept using the closed-form least-squares solution."""
    # Calculate the two parameters without external ML packages.
    x_values = [x for x, _ in rows]
    y_values = [y for _, y in rows]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    if denominator == 0:
        raise ValueError("The feature values must not all be identical.")
    slope = sum((x - x_mean) * (y - y_mean) for x, y in rows) / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate a tiny linear regression model.")
    parser.add_argument("--data", type=Path, required=True, help="CSV file with size_sqft and price_k columns")
    parser.add_argument("--config", type=Path, required=True, help="JSON job configuration")
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for predictions and metrics")
    args = parser.parse_args()

    # Terraform creates this JSON file; Python owns the ML behavior.
    config = json.loads(args.config.read_text(encoding="utf-8"))
    rows = read_rows(args.data)
    slope, intercept = fit_linear_regression(rows)
    predictions = [(x, y, slope * x + intercept) for x, y in rows]
    # Mean absolute error is easy to understand for a first ML lesson.
    mae = sum(abs(actual - predicted) for _, actual, predicted in predictions) / len(predictions)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = args.output_dir / "predictions.csv"
    metrics_path = args.output_dir / "metrics.json"

    # Write artifacts that a later pipeline step could upload or evaluate.
    with predictions_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["size_sqft", "actual_price_k", "predicted_price_k"])
        writer.writerows(predictions)

    metrics = {
        "run_name": config.get("run_name", "unnamed-run"),
        "model": config.get("model", "linear_regression"),
        "rows": len(rows),
        "slope": slope,
        "intercept": intercept,
        "mean_absolute_error": mae,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    print(f"Completed ML run: {metrics['run_name']}")
    print(f"Model: y = {slope:.4f} * x + {intercept:.4f}")
    print(f"Mean absolute error: {mae:.4f}")
    print(f"Metrics: {metrics_path}")
    print(f"Predictions: {predictions_path}")


if __name__ == "__main__":
    main()
