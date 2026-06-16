from pathlib import Path

import joblib
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


matplotlib.use("Agg")
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

DATA_PATH = Path("data/air_quality_dataset.csv")
MODEL_PATH = Path("models/air_quality_model.joblib")
RESULTS_DIR = Path("static/results")

FEATURE_COLUMNS = [
    "temperature",
    "humidity",
    "wind_speed",
    "rainfall",
    "traffic_index",
    "industrial_index",
    "pm25",
    "pm10",
    "no2",
    "so2",
    "ozone",
]
LABEL_COLUMN = "quality_level"
LABELS = ["优", "良", "轻度污染", "中度及以上污染"]


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in FEATURE_COLUMNS + ["aqi"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["temperature"] = df["temperature"].clip(-10, 45)
    df["humidity"] = df["humidity"].clip(0, 100)
    df["wind_speed"] = df["wind_speed"].clip(0, 15)
    df["rainfall"] = df["rainfall"].clip(0, 50)
    df["traffic_index"] = df["traffic_index"].clip(0, 100)
    df["industrial_index"] = df["industrial_index"].clip(0, 100)
    df["pm25"] = df["pm25"].clip(0, 300)
    df["pm10"] = df["pm10"].clip(0, 400)
    df["no2"] = df["no2"].clip(0, 150)
    df["so2"] = df["so2"].clip(0, 100)
    df["ozone"] = df["ozone"].clip(0, 200)
    df = df.dropna(subset=[LABEL_COLUMN])
    return df


def make_preprocessor() -> ColumnTransformer:
    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipe, FEATURE_COLUMNS),
        ]
    )


def train_and_evaluate() -> tuple[Pipeline, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series]:
    df = clean_data(pd.read_csv(DATA_PATH))
    x = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=7,
        stratify=y,
    )

    candidates = {
        "逻辑回归": LogisticRegression(max_iter=1000, class_weight="balanced"),
        "随机森林": RandomForestClassifier(n_estimators=180, max_depth=8, random_state=7, class_weight="balanced"),
        "K近邻": KNeighborsClassifier(n_neighbors=7),
    }

    rows = []
    fitted_models: dict[str, Pipeline] = {}
    for name, estimator in candidates.items():
        pipe = Pipeline(
            steps=[
                ("preprocess", make_preprocessor()),
                ("model", estimator),
            ]
        )
        pipe.fit(x_train, y_train)
        pred = pipe.predict(x_test)
        rows.append(
            {
                "model": name,
                "accuracy": round(accuracy_score(y_test, pred), 4),
                "macro_f1": round(f1_score(y_test, pred, average="macro"), 4),
            }
        )
        fitted_models[name] = pipe

    metrics = pd.DataFrame(rows).sort_values(["macro_f1", "accuracy"], ascending=False)
    best_model = fitted_models[metrics.iloc[0]["model"]]
    return best_model, metrics, df, x_test, y_test


def save_figures(model: Pipeline, metrics: pd.DataFrame, df: pd.DataFrame, x_test: pd.DataFrame, y_test: pd.Series) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(RESULTS_DIR / "model_metrics.csv", index=False, encoding="utf-8-sig")

    ax = metrics.plot(kind="bar", x="model", y=["accuracy", "macro_f1"], figsize=(7.2, 4.2), color=["#2563eb", "#f97316"])
    ax.set_title("模型性能对比")
    ax.set_xlabel("")
    ax.set_ylabel("得分")
    ax.set_ylim(0, 1.05)
    ax.legend(["准确率", "Macro-F1"])
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "model_comparison.png", dpi=180)
    plt.close()

    pred = model.predict(x_test)
    ConfusionMatrixDisplay.from_predictions(y_test, pred, labels=LABELS, cmap="Greens", colorbar=False)
    plt.title("最佳模型混淆矩阵")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "confusion_matrix.png", dpi=180)
    plt.close()

    dist = df[LABEL_COLUMN].value_counts().reindex(LABELS)
    plt.figure(figsize=(6.6, 4.0))
    plt.bar(dist.index, dist.values, color=["#22c55e", "#84cc16", "#f59e0b", "#ef4444"])
    plt.title("空气质量等级分布")
    plt.xlabel("空气质量等级")
    plt.ylabel("记录数")
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "quality_distribution.png", dpi=180)
    plt.close()

    estimator = model.named_steps["model"]
    if hasattr(estimator, "feature_importances_"):
        importance = pd.Series(estimator.feature_importances_, index=FEATURE_COLUMNS).sort_values(ascending=False).head(10)
        title = "空气质量预测关键因素"
        xlabel = "重要性"
    else:
        importance = df[FEATURE_COLUMNS + ["aqi"]].corr(numeric_only=True)["aqi"].drop("aqi").abs().sort_values(ascending=False).head(10)
        title = "AQI相关关键因素"
        xlabel = "相关性强度"

    plt.figure(figsize=(7.0, 4.4))
    plt.barh(importance.index[::-1], importance.values[::-1], color="#0ea5e9")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "feature_importance.png", dpi=180)
    plt.close()


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError("请先运行 python generate_dataset.py 生成数据集。")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    model, metrics, df, x_test, y_test = train_and_evaluate()
    joblib.dump(model, MODEL_PATH)
    save_figures(model, metrics, df, x_test, y_test)

    print("模型训练完成。")
    print("模型对比结果：")
    print(metrics.to_string(index=False))
    print(f"最佳模型已保存：{MODEL_PATH}")
    print(f"可视化结果已保存：{RESULTS_DIR}")


if __name__ == "__main__":
    main()
