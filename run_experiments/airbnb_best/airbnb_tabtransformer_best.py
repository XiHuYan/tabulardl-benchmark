import os
import pickle
import sys
from datetime import datetime
from pathlib import Path
from time import time

import numpy as np
import pandas as pd
import torch
from pytorch_widedeep import Trainer
from pytorch_widedeep.callbacks import EarlyStopping, LRHistory, ModelCheckpoint
from pytorch_widedeep.models import TabTransformer, Wide, WideDeep
from pytorch_widedeep.preprocessing import TabPreprocessor, WidePreprocessor
from sklearn.metrics import mean_squared_error

sys.path.append(
    os.path.abspath("/home/ubuntu/Projects/tabulardl-benchmark/run_experiments")
)  # isort:skipimport pickle
from airbnb_tabmlp_best import load_dataset, set_dirs  # noqa: E402
from general_utils.utils import (  # noqa: E402
    read_best_model_args,
    set_lr_scheduler,
    set_optimizer,
)

pd.options.display.max_columns = 100

use_cuda = torch.cuda.is_available()


ROOTDIR = Path("/home/ubuntu/Projects/tabulardl-benchmark")
WORKDIR = Path(os.getcwd())
PROCESSED_DATA_DIR = ROOTDIR / "processed_data/airbnb/"


def prepare_data(results_dir):

    train, test = load_dataset()

    args = read_best_model_args(results_dir)

    cat_embed_cols = []
    for col in train.columns:
        if (
            (train[col].dtype == "O" or train[col].dtype == "int")
            and train[col].nunique() > 6
            and col != "target"
        ):
            cat_embed_cols.append(col)

    cat_embed_cols = list(sorted(cat_embed_cols + ["minimum_nights_median"]))

    wide_cols = []
    for col in train.columns:
        if (
            (train[col].dtype == "O" or train[col].dtype == "int")
            and train[col].nunique() < 40
            and col != "target"
        ):
            wide_cols.append(col)

    wide_cols = list(sorted(wide_cols + ["bedrooms", "beds"]))

    num_cols = [
        c for c in train.columns if c not in cat_embed_cols + wide_cols + ["target"]
    ]

    prepare_wide = WidePreprocessor(wide_cols)
    X_wide_train = prepare_wide.fit_transform(train)
    X_wide_test = prepare_wide.transform(test)

    prepare_tab = TabPreprocessor(
        embed_cols=cat_embed_cols,
        continuous_cols=num_cols,
        scale=True,
        for_tabtransformer=True,
    )
    X_tab_train = prepare_tab.fit_transform(train)
    X_tab_test = prepare_tab.transform(test)

    y_train = train.target.values
    y_test = test.target.values

    X_train_d = {"X_wide": X_wide_train, "X_tab": X_tab_train, "target": y_train}
    X_test_d = {"X_wide": X_wide_test, "X_tab": X_tab_test, "target": y_test}

    wide_dim = np.unique(X_wide_train).shape[0]
    mlp_hidden_dims_same = len(cat_embed_cols) * args.input_dim + len(num_cols)

    return (
        args,
        prepare_tab,
        X_train_d,
        X_test_d,
        wide_dim,
        mlp_hidden_dims_same,
    )


def set_model(args, prepare_tab, wide_dim, mlp_hidden_dims_same):

    wide = Wide(wide_dim=wide_dim)

    if args.mlp_hidden_dims == "same":
        mlp_hidden_dims = [
            mlp_hidden_dims_same,
            mlp_hidden_dims_same,
            (mlp_hidden_dims_same) // 2,
        ]
    elif args.mlp_hidden_dims == "None":
        mlp_hidden_dims = None
    else:
        mlp_hidden_dims = eval(args.mlp_hidden_dims)

    deeptabular = TabTransformer(
        column_idx=prepare_tab.column_idx,
        embed_input=prepare_tab.embeddings_input,
        embed_dropout=args.embed_dropout,
        continuous_cols=prepare_tab.continuous_cols,
        full_embed_dropout=args.full_embed_dropout,
        shared_embed=args.shared_embed,
        add_shared_embed=args.add_shared_embed,
        frac_shared_embed=args.frac_shared_embed,
        input_dim=args.input_dim,
        n_heads=args.n_heads,
        n_blocks=args.n_blocks,
        dropout=args.dropout,
        ff_hidden_dim=4 * args.input_dim
        if not args.ff_hidden_dim
        else args.ff_hidden_dim,
        transformer_activation=args.transformer_activation,
        mlp_hidden_dims=mlp_hidden_dims,
        mlp_activation=args.mlp_activation,
        mlp_batchnorm=args.mlp_batchnorm,
        mlp_batchnorm_last=args.mlp_batchnorm_last,
        mlp_linear_first=args.mlp_linear_first,
    )
    model = WideDeep(wide=wide, deeptabular=deeptabular)

    return model


def run_experiment_and_save(
    model, model_name, results_dir, models_dir, args, X_train_d, X_test_d
):

    optimizers = set_optimizer(model, args)

    steps_per_epoch = (X_train_d["X_tab"].shape[0] // args.batch_size) + 1
    lr_schedulers = set_lr_scheduler(optimizers, steps_per_epoch, args)

    early_stopping = EarlyStopping(
        monitor=args.monitor,
        min_delta=args.early_stop_delta,
        patience=args.early_stop_patience,
    )

    model_checkpoint = ModelCheckpoint(
        filepath=str(models_dir / "best_model"),
        monitor=args.monitor,
        save_best_only=True,
        max_save=1,
    )

    trainer = Trainer(
        model,
        objective="regression",
        optimizers=optimizers,
        lr_schedulers=lr_schedulers,
        reducelronplateau_criterion=args.monitor.split("_")[-1],
        callbacks=[early_stopping, model_checkpoint, LRHistory(n_epochs=args.n_epochs)],
    )

    start = time()
    trainer.fit(
        X_train=X_train_d,
        X_val=X_test_d,
        n_epochs=args.n_epochs,
        batch_size=args.batch_size,
        validation_freq=args.eval_every,
    )
    runtime = time() - start

    y_pred = trainer.predict(X_wide=X_test_d["X_wide"], X_tab=X_test_d["X_tab"])

    rmse = np.sqrt(mean_squared_error(X_test_d["target"], y_pred))
    print(f"rmse with the best model: {rmse}")

    if args.save_results:
        suffix = str(datetime.now()).replace(" ", "_").split(".")[:-1][0]
        filename = "_".join(["airbnb", model_name, "best", suffix]) + ".p"
        results_d = {}
        results_d["args"] = args
        results_d["rmse"] = rmse
        results_d["early_stopping"] = early_stopping
        results_d["trainer_history"] = trainer.history
        results_d["trainer_lr_history"] = trainer.lr_history
        results_d["runtime"] = runtime
        with open(results_dir / filename, "wb") as f:
            pickle.dump(results_d, f)


if __name__ == "__main__":

    model_name = "tabtransformer"

    results_dir, models_dir = set_dirs(model_name)

    train, test = load_dataset()

    (
        args,
        prepare_tab,
        X_train_d,
        X_test_d,
        wide_dim,
        mlp_hidden_dims_same,
    ) = prepare_data(results_dir)

    model = set_model(args, prepare_tab, wide_dim, mlp_hidden_dims_same)

    run_experiment_and_save(
        model,
        model_name,
        results_dir,
        models_dir,
        args,
        X_train_d,
        X_test_d,
    )
