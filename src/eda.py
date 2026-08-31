"""Generate exploratory data analysis reports for the heart disease dataset."""

from math import ceil
from pathlib import Path

import matplotlib
import pandas as pd
import seaborn as sns


# Use a non-interactive backend so the script works in terminal environments.
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "data" / "heart_disease.csv"
REPORTS_DIRECTORY = PROJECT_ROOT / "reports" / "eda"
TARGET_COLUMN = "target"


def create_output_directory() -> None:
    """Create the EDA report directory when it is not already present."""
    REPORTS_DIRECTORY.mkdir(parents=True, exist_ok=True)


def save_figure(figure: plt.Figure, filename: str) -> None:
    """Save a figure at high resolution and report its location."""
    output_path = REPORTS_DIRECTORY / filename
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    print(f"Generated: {output_path.relative_to(PROJECT_ROOT)}")


def print_dataset_overview(dataframe: pd.DataFrame) -> None:
    """Print the basic structure and quality checks for the dataset."""
    print("Dataset shape:", dataframe.shape)
    print("Number of rows:", len(dataframe))
    print("Number of columns:", len(dataframe.columns))
    print("Column names:", dataframe.columns.tolist())
    print("Data types:")
    print(dataframe.dtypes)
    print("Missing values per column:")
    print(dataframe.isnull().sum())
    print("Duplicate row count:", dataframe.duplicated().sum())


def save_descriptive_statistics(dataframe: pd.DataFrame) -> None:
    """Create and save descriptive statistics for every column."""
    summary_path = REPORTS_DIRECTORY / "dataset_summary.csv"
    dataframe.describe(include="all").to_csv(summary_path)
    print(f"Generated: {summary_path.relative_to(PROJECT_ROOT)}")


def create_target_distribution(dataframe: pd.DataFrame) -> None:
    """Create a bar chart showing samples in each target class."""
    figure, axis = plt.subplots(figsize=(8, 6))
    sns.countplot(data=dataframe, x=TARGET_COLUMN, hue=TARGET_COLUMN,
                  palette="Set2", legend=False, ax=axis)
    axis.set_title("Target Class Distribution")
    axis.set_xlabel("Target Class")
    axis.set_ylabel("Number of Patients")
    save_figure(figure, "target_distribution.png")


def create_age_distribution(dataframe: pd.DataFrame) -> None:
    """Create a histogram that shows the distribution of patient ages."""
    figure, axis = plt.subplots(figsize=(8, 6))
    sns.histplot(data=dataframe, x="age", bins=20, kde=True,
                 color="steelblue", ax=axis)
    axis.set_title("Age Distribution")
    axis.set_xlabel("Age (years)")
    axis.set_ylabel("Number of Patients")
    save_figure(figure, "age_distribution.png")


def create_correlation_heatmap(dataframe: pd.DataFrame,
                               numerical_columns: list[str]) -> None:
    """Create a heatmap of correlations among numerical features."""
    correlation_matrix = dataframe[numerical_columns].corr()
    figure, axis = plt.subplots(figsize=(14, 11))
    sns.heatmap(correlation_matrix, cmap="coolwarm", center=0,
                annot=True, fmt=".2f", square=True, linewidths=0.5,
                cbar_kws={"label": "Correlation"}, ax=axis)
    axis.set_title("Correlation Heatmap")
    axis.set_xlabel("Features")
    axis.set_ylabel("Features")
    save_figure(figure, "correlation_heatmap.png")


def create_boxplots(dataframe: pd.DataFrame,
                    numerical_columns: list[str]) -> None:
    """Create boxplots for every numerical feature."""
    column_count = 3
    row_count = ceil(len(numerical_columns) / column_count)
    figure, axes = plt.subplots(row_count, column_count,
                                figsize=(15, 4 * row_count))
    flattened_axes = axes.flatten()

    for axis, column in zip(flattened_axes, numerical_columns):
        sns.boxplot(data=dataframe, y=column, color="skyblue", ax=axis)
        axis.set_title(f"Boxplot of {column}")
        axis.set_xlabel("Feature")
        axis.set_ylabel(column)

    for axis in flattened_axes[len(numerical_columns):]:
        axis.remove()

    figure.suptitle("Boxplots of Numerical Features", fontsize=16)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    save_figure(figure, "boxplots.png")


def create_feature_histograms(dataframe: pd.DataFrame,
                              numerical_columns: list[str]) -> None:
    """Create histograms for every numerical feature."""
    column_count = 3
    row_count = ceil(len(numerical_columns) / column_count)
    figure, axes = plt.subplots(row_count, column_count,
                                figsize=(15, 4 * row_count))
    flattened_axes = axes.flatten()

    for axis, column in zip(flattened_axes, numerical_columns):
        sns.histplot(data=dataframe, x=column, bins=20, kde=True,
                     color="mediumpurple", ax=axis)
        axis.set_title(f"Distribution of {column}")
        axis.set_xlabel(column)
        axis.set_ylabel("Frequency")

    for axis in flattened_axes[len(numerical_columns):]:
        axis.remove()

    figure.suptitle("Histograms of Numerical Features", fontsize=16)
    figure.tight_layout(rect=(0, 0, 1, 0.97))
    save_figure(figure, "feature_histograms.png")


def print_target_analysis(dataframe: pd.DataFrame,
                          numerical_columns: list[str]) -> None:
    """Print target counts and each numerical feature's target correlation."""
    print("Target class counts:")
    print(dataframe[TARGET_COLUMN].value_counts().sort_index())
    print("Correlation of each feature with the target variable:")
    print(
        dataframe[numerical_columns]
        .corrwith(dataframe[TARGET_COLUMN])
        .drop(TARGET_COLUMN, errors="ignore")
        .sort_values(ascending=False)
    )


def main() -> None:
    """Run the complete EDA workflow and save all reports and figures."""
    # Load the dataset and prepare the output location.
    dataframe = pd.read_csv(DATASET_PATH)
    create_output_directory()
    sns.set_theme(style="whitegrid")

    # Identify column types used for analysis and plotting.
    numerical_columns = dataframe.select_dtypes(
        include="number"
    ).columns.tolist()
    categorical_columns = dataframe.select_dtypes(
        exclude="number"
    ).columns.tolist()

    # Print data structure, quality checks, and descriptive information.
    print_dataset_overview(dataframe)
    print("Descriptive statistics:")
    print(dataframe.describe(include="all"))
    print("Numerical columns:", numerical_columns)
    print("Categorical columns:", categorical_columns)
    print_target_analysis(dataframe, numerical_columns)

    # Save the tabular EDA report and requested visualizations.
    save_descriptive_statistics(dataframe)
    create_target_distribution(dataframe)
    create_age_distribution(dataframe)
    create_correlation_heatmap(dataframe, numerical_columns)
    create_boxplots(dataframe, numerical_columns)
    create_feature_histograms(dataframe, numerical_columns)

    print("EDA completed successfully.")
    print("Generated files:")
    print("- dataset_summary.csv")
    print("- target_distribution.png")
    print("- age_distribution.png")
    print("- correlation_heatmap.png")
    print("- boxplots.png")
    print("- feature_histograms.png")


if __name__ == "__main__":
    main()
