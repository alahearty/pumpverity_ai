import argparse
import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from petrosense_ml.dataset import generate_dataset
from petrosense_ml.evaluation import comparison_report, evaluate_model
from petrosense_ml.export import build_registration_manifest, export_artifacts
from petrosense_ml.register import password_from_environment, register_manifest
from petrosense_ml.train import build_trained_models, score_models

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# Stage 4 model comparison (synthetic)",
        "",
        f"Generated: {report['generated_at']}",
        f"Dataset: {report['dataset']['dataset_version']}",
        f"Provenance: **{report['dataset']['provenance']}**",
        f"Feature contract: {report['feature_contract']['version']}",
        "",
        "> " + report["warning"],
        "",
        "| Model | Balanced accuracy | Macro-F1 | Coverage | Risk | False-alert rate |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, metrics in report["models"].items():
        lines.append(
            f"| {name} | {metrics['balanced_accuracy']:.3f} | "
            f"{metrics['macro_f1']:.3f} | {metrics['coverage']:.3f} | "
            f"{metrics['risk']:.3f} | {metrics['false_alert_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Metrics are computed on accepted decisions after uncertainty abstention. "
            "Coverage is the fraction accepted; risk is the error rate among accepted samples.",
            "",
            f"Split: {report['split']['description']}",
            f"Train runs: {report['split']['train_runs']}; test runs: "
            f"{report['split']['test_runs']}; test samples: {report['split']['test_samples']}.",
            "",
            "The lightweight linear model is selected for Stage 4 edge deployment. The threshold "
            "baseline and random forest are comparison candidates. No real-pump performance claim "
            "is supported by this report.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_pipeline(seeds: range, *, register: bool, api_base: str, email: str) -> int:
    frame, metadata = generate_dataset(seeds=seeds)
    trained = build_trained_models(frame)
    scores = score_models(trained)
    test = trained.split.test
    labels = test["label"].to_numpy()
    scenarios = test["scenario"].to_numpy()
    metrics_by_model = {
        name: evaluate_model(name, values, labels, scenario=scenarios)
        for name, values in scores.items()
    }

    dataset_dir = REPO_ROOT / "ml" / "datasets"
    artifact_dir = REPO_ROOT / "ml" / "artifacts"
    report_dir = REPO_ROOT / "ml" / "reports"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(dataset_dir / "stage4_synthetic_features.csv", index=False)

    exported = export_artifacts(trained, metrics_by_model, artifact_dir)
    manifest = build_registration_manifest(exported, metrics_by_model)
    report = comparison_report(metrics_by_model)
    report.update(
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset": asdict(metadata),
            "split": {
                "description": trained.split.split_description,
                "train_runs": trained.split.train_groups,
                "test_runs": trained.split.test_groups,
                "train_samples": len(trained.split.train),
                "test_samples": len(test),
            },
            "feature_contract": metadata.feature_contract,
            "selected_edge_model": "petrosense-linear 0.1.0",
        }
    )
    report_path = report_dir / "stage4-model-comparison.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown(report, report_dir / "stage4-model-comparison.md")
    (report_dir / "stage4-registration-manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    print("Stage 4 synthetic model comparison")
    for name, metrics in metrics_by_model.items():
        print(
            f"  {name:<20} bal_acc={metrics['balanced_accuracy']:.3f} "
            f"macro_f1={metrics['macro_f1']:.3f} coverage={metrics['coverage']:.3f} "
            f"risk={metrics['risk']:.3f}"
        )
    print(f"Report: {report_path}")
    print(f"Selected edge artefact: {exported['linear']['path']}")

    if register:
        password = password_from_environment()
        results = register_manifest(
            manifest, api_base=api_base, email=email, password=password
        )
        print("Model registry registration:")
        for result in results:
            print(
                f"  {result['model_code']} v{result['version']} -> {result['status']}"
            )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train and evaluate PUMPVERITY Stage 4 synthetic models"
    )
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument(
        "--email",
        default=os.environ.get("PETROSENSE_ML_EMAIL", "researcher@petrosense.local"),
    )
    args = parser.parse_args(argv)
    if args.seeds < 5:
        raise SystemExit("At least 5 seeds are required")
    return run_pipeline(
        range(1, args.seeds + 1),
        register=args.register,
        api_base=args.api_base,
        email=args.email,
    )


if __name__ == "__main__":
    raise SystemExit(main())
