from sklearn.model_selection import train_test_split
from sklearn.datasets import load_diabetes
import click

@click.command()
@click.option("--output_train_data_features", required=True)
@click.option("--output_train_data_labels", required=True)
def load(
    output_train_data_features,
    output_train_data_labels,
):

    X, y = load_diabetes(return_X_y=True, as_frame=True)

    X_train, X_test, y_train, y_test = train_test_split(X, y,
                                                        test_size=0.2,
                                                        random_state=0)
    data = {"train": {"X": X_train, "y": y_train},
            "test": {"X": X_test, "y": y_test}}

    # Write train data to 
    X_train.to_csv(output_train_data_features, index=False)
    y_train.to_csv(output_train_data_labels, index=False)

    return data

if __name__ == "__main__":
    load()
