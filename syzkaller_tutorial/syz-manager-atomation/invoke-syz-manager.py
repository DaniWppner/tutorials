#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
import json
from pathlib import Path
import difflib
import signal
import re
from datetime import datetime

# Constants for hardcoded paths and filenames
REPRO_PACKAGE_DIRNAME = "repro_package"
CORPUS_FILENAME = "corpus.db"
REAL_CFG_FILENAME = "syzkaller.cfg"
LINUX_CONFIG_FILENAME = ".config"
LINUX_COMMIT_FILENAME = "linux_commit_difference.json"
LINUX_DIFF_FILENAME = "linux_diff_from_ancestor.patch"
SYZKALLER_COMMIT_FILENAME = "syzkaller_commit_difference.json"
SYZKALLER_DIFF_FILENAME = "syzkaller_diff_from_ancestor.patch"
SYZ_MANAGER_LOG_FILENAME = "syz-manager.log"
README_FILENAME = "README.md"
SYZ_MANAGER_BIN_RELATIVE_PATH = ["bin", "syz-manager"]
BZIMAGE_RELATIVE_PATH = ["arch", "x86", "boot", "bzImage"]
# Created in the work dir on resume: elapsed time is derived from the log's first/last timestamps,
# which is only valid for a campaign that was resumed once
RESUMED_FLAG_FILENAME = ".resumed"
LOG_TIMESTAMP_RE = re.compile(r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) ")

# Update if it would make reproduction packages from the previous version incompatible
INVOKE_SYZ_MANAGER_VERSION = "1.1.1"


def log(*args, **kwargs):
    """Print log messages in magenta (stdout) or red (stderr)."""
    text = " ".join(str(a) for a in args)
    file_arg = kwargs.get("file")

    if file_arg is None or file_arg == sys.stdout:
        print(f"\033[35m{text}\033[0m", **kwargs)
    elif file_arg == sys.stderr:
        print(f"\033[31m{text}\033[0m", **kwargs)
    else:
        print(*args, **kwargs)


def color_diff_line(line: str) -> str:
    if line.startswith("+") and not line.startswith("+++"):
        return f"\033[32m{line}\033[0m"  # Green
    elif line.startswith("-") and not line.startswith("---"):
        return f"\033[31m{line}\033[0m"  # Red
    elif line.startswith("@"):
        return f"\033[36m{line}\033[0m"  # Cyan
    else:
        return line


class ReproductionError(Exception):
    """Raised when the reproduction package is invalid or inconsistent."""

    pass


class ConfigurationError(Exception):
    pass


def load_config(config_path: Path, required_keys: list[str]) -> dict[str, str]:
    """
    Load configuration from config.json file in the current working directory.
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ConfigurationError(
                    f"Missing required keys in config file: {missing_keys}"
                )
            return config
    except FileNotFoundError:
        raise ConfigurationError(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError:
        raise ConfigurationError(f"Invalid JSON in configuration file {config_path}")


def prompt_for_confirm() -> bool:
    while True:
        response = input("\nDo you want to continue? [y/N]: ").lower()
        if response in ["y", "yes"]:
            return True
        if response in ["", "n", "no"]:
            return False
        log("Please answer 'y' or 'n'")


def confirm_paths(required_keys: dict[str, Path]) -> bool:
    """
    Ask user to confirm the paths that will be used.
    """

    for key, val in required_keys.items():
        log(f"The following {key} source path will be used:\n {str(val)}")
        if not prompt_for_confirm():
            return False
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automate execution of syz-manager with a reproducible working tree."
    )
    parser.add_argument(
        "--linux-src", help="Path to the Linux source tree (overrides config file)"
    )
    parser.add_argument(
        "--cfg-template", required=True, help="Path to the syzkaller .cfg template"
    )
    parser.add_argument(
        "--syzkaller-src",
        help="Path to the syzkaller source tree (overrides config file)",
    )
    parser.add_argument(
        "--work-name", required=True, help="Name to use for the working tree"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to the configuration file (default: config.json)",
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        type=int,
        default=10,
        help="syzkaller verbosity level (default max)",
    )
    parser.add_argument(
        "--run-hours",
        type=float,
        help="Length of each campaign in hours (enforces clean initial state and archives runs)",
    )
    parser.add_argument(
        "--N-runs",
        type=int,
        help="Desired amount of campaigns to run (default: infinite)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continue an interrupted --run-hours campaign: only the remaining time is run, "
        "and --N-runs counts the campaigns already archived in the working directory",
    )
    return parser.parse_args()


def copy_and_modify_cfg(
    cfg_template: Path, work_dir: Path, syzkaller_path: Path, linux_src_path: Path
) -> str:
    """
    Return expected contents for real.cfg after copying/modifying.
    """
    with open(cfg_template, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            raise ConfigurationError(
                f"Invalid JSON in syzkaller cfg template file {cfg_template}"
            )

    config["workdir"] = str(work_dir)
    config["syzkaller"] = str(syzkaller_path)
    config["kernel_src"] = str(linux_src_path)
    config["kernel_obj"] = str(linux_src_path)
    bzimage_path = Path(linux_src_path).joinpath(*BZIMAGE_RELATIVE_PATH)
    config["vm"]["kernel"] = str(bzimage_path)

    return json.dumps(config, indent=4)


def get_linux_config(linux_src: Path) -> str:
    """
    Return contents of the Linux .config file.
    """
    cfg_path = linux_src / ".config"
    if not cfg_path.exists():
        raise ConfigurationError(f"Linux .config file not found at {cfg_path}")
    return cfg_path.read_text()


def get_closest_upstream_ancestor(
    repo_source_root: Path,
) -> tuple[str, str, str] | None:
    """
    Find the most recent common ancestor with any branch that has an upstream.
    Returns (ancestor_hash, ancestor_message, remote_url) or None if not found.
    """
    output = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo_source_root),
            "for-each-ref",
            "--format=%(refname:short) %(upstream:short)",
            "refs/heads/",
        ],
        text=True,
    ).strip()

    candidates = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            candidates.append((parts[0], parts[1]))

    if not candidates:
        return None

    best_ancestor = None
    min_distance = float("inf")
    best_cand_branch = None

    for cand_branch, cand_upstream in candidates:
        try:
            ancestor = subprocess.check_output(
                [
                    "git",
                    "-C",
                    str(repo_source_root),
                    "merge-base",
                    "HEAD",
                    cand_upstream,
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()

            distance = int(
                subprocess.check_output(
                    [
                        "git",
                        "-C",
                        str(repo_source_root),
                        "rev-list",
                        "--count",
                        f"{ancestor}..HEAD",
                    ],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            )

            if distance < min_distance:
                min_distance = distance
                best_ancestor = ancestor
                best_cand_branch = cand_branch
        except subprocess.CalledProcessError:
            continue

    if best_ancestor is None or best_cand_branch is None:
        return None

    ancestor_msg = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "log", "-1", best_ancestor, "--pretty=%s"],
        text=True,
    ).strip()

    remote_name = get_remote(repo_source_root, best_cand_branch)
    if remote_name is None:
        return None

    remote_url = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "remote", "get-url", remote_name],
        text=True,
    ).strip()

    return best_ancestor, ancestor_msg, remote_url, best_cand_branch


def get_syzkaller_history_info(repo_source_root: Path) -> dict[str, str | None]:
    """
    Return commit info up to the local HEAD from the syzkaller repo.
    For syzkaller we assume we are on a branch that is tracked remotely,
    or we find the closest ancestor that is.
    """
    branch = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "rev-parse", "--abbrev-ref", "HEAD"],
        text=True,
    ).strip()

    remote_name = get_remote(repo_source_root, branch)

    if remote_name is not None:
        ancestor_branch = branch
        remote_url = subprocess.check_output(
            ["git", "-C", str(repo_source_root), "remote", "get-url", remote_name],
            text=True,
        ).strip()

        ancestor_hash = subprocess.check_output(
            ["git", "-C", str(repo_source_root), "rev-parse", "@{u}"], text=True
        ).strip()
        ancestor_msg = subprocess.check_output(
            ["git", "-C", str(repo_source_root), "log", "-1", "@{u}", "--pretty=%s"],
            text=True,
        ).strip()
    else:
        closest_ancestor_info = get_closest_upstream_ancestor(repo_source_root)
        if closest_ancestor_info is None:
            raise ConfigurationError(
                f"Current branch {branch} in syzkaller repo at {repo_source_root} has no upstream, "
                "and no common ancestor with any upstream branch was found."
            )
        ancestor_hash, ancestor_msg, remote_url, ancestor_branch = closest_ancestor_info

    untracked_commits = commits_to_head(repo_source_root, ancestor_hash)

    ancestor_info = {
        "hash": ancestor_hash,
        "message": ancestor_msg,
        "branch": ancestor_branch,
        "upstream": remote_url,
    }
    difference = {"distance": len(untracked_commits), "commits": untracked_commits}
    return {"last_ancestor": ancestor_info, "difference": difference}


def get_linux_history_info(repo_source_root: Path) -> dict[str, str | None]:
    """
    Return commit info up to the local HEAD from the Linux repo.
    For Linux we report the difference from the closest tag.
    """

    last_ancestor = get_last_tag(repo_source_root)
    untracked_commits = commits_to_head(repo_source_root, last_ancestor["commit_hash"])
    ancestor_info = {
        "hash": last_ancestor["commit_hash"],
        "message": last_ancestor["commit_message"],
        "tag": last_ancestor["tag"],
    }
    difference = {"distance": len(untracked_commits), "commits": untracked_commits}

    return {"last_ancestor": ancestor_info, "difference": difference}


def get_remote(repo_source_root: Path, branch: str) -> str | None:
    """
    Return the remote name for the given branch, or None if it has no remote.
    """
    try:
        remote_name = subprocess.check_output(
            ["git", "-C", str(repo_source_root), "config", f"branch.{branch}.remote"],
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        remote_name = None
    return remote_name


def get_script_repo_info() -> tuple[str, str]:
    """Return the commit hash and remote URL of the repo hosting this script."""
    script_dir = Path(__file__).parent.resolve()
    try:
        commit_hash = subprocess.check_output(
            ["git", "-C", str(script_dir), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        branch = subprocess.check_output(
            ["git", "-C", str(script_dir), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        remote_name = get_remote(script_dir, branch)
        if remote_name:
            remote_url = subprocess.check_output(
                ["git", "-C", str(script_dir), "remote", "get-url", remote_name],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        else:
            remote_url = "unknown"

    except subprocess.CalledProcessError:
        commit_hash = "unknown"
        remote_url = "unknown"

    return commit_hash, remote_url


def commits_to_head(repo_source_root: Path, ancestor_hash: str) -> list[dict[str, str]]:
    """
    Return list of commits from ancestor_hash (exclusive) to HEAD (inclusive).
    """
    commit_lines = (
        subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_source_root),
                "log",
                f"{ancestor_hash}..HEAD",
                "--pretty=%H,%s",
            ],
            text=True,
        )
        .strip()
        .splitlines()
    )

    commits = []
    for line in commit_lines:
        commit_hash, commit_msg = line.split(",", 1)
        commits.append({"hash": commit_hash, "message": commit_msg})
    return commits


def get_last_tag(repo_source_root: Path) -> dict[str, str]:
    """
    Return the closest tag, and the commit hash and message at that tag.
    """
    og_tag = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "describe"], text=True
    ).strip()
    tag = og_tag.split("-")[0]

    cmd = [
        "git",
        "-C",
        str(repo_source_root),
        "log",
        "-1",
        "--pretty=%H,%s",
        f"tags/{tag}",
    ]
    try:
        commit_hash_and_message = subprocess.check_output(cmd, text=True).strip()
    except subprocess.CalledProcessError as e:
        raise ConfigurationError(
            "Getting the linux commit of the closest tag failed, probably "
            f"because current tag is {og_tag} but {tag} does not exist yet.\n\n"
            "command ran:\n"
            f"  {' '.join(cmd)}\n\n"
            "received output:\n"
            f"  {e.output}"
        )

    commit_hash, commit_msg = commit_hash_and_message.split(",", 1)

    return {
        "commit_hash": commit_hash,
        "tag": tag,
        "commit_message": commit_msg,
    }


def create_patch_from_info(
    history_info: dict[str, str], output_path: Path, repo_source_root: Path
):
    """
    Create a patch file from the ancestor to HEAD using git diff
    """
    if history_info["difference"]["distance"] == 0:
        log(
            f"[info] No unpushed commits in repo at {repo_source_root}, skipping patch creation."
        )
        return
    else:
        ancestor_hash = history_info["last_ancestor"]["hash"]
        with open(output_path, "w") as f:
            subprocess.run(
                ["git", "-C", str(repo_source_root), "diff", f"{ancestor_hash}..HEAD"],
                stdout=f,
                check=True,
            )
        log(f"[write] create git patch at {output_path}")


def get_existing_work_dir(work_dir: Path) -> tuple[Path | None, Path | None]:
    repro_dir = work_dir / REPRO_PACKAGE_DIRNAME
    corpus_db = work_dir / CORPUS_FILENAME

    if not repro_dir.exists():
        repro_dir = None
        log(
            f"[warning]: Directory with name {work_dir} already exists but reproduction package is missing."
        )
        log(
            f"[warning]: This will create the syzkaller files along the existing contents of {work_dir}."
        )

    if not corpus_db.exists():
        corpus_db = None

    return repro_dir, corpus_db


def check_repro_package(repro_dir: Path, expected_files: dict[Path, str]):
    """
    Check if the working tree exists and validate reproduction package contents.
    """
    MAX_CONFIG_DIFF_LINES = 10
    errors = []

    for fpath, expected_content in expected_files.items():
        if not fpath.exists():
            errors.append(
                f"Expected reproduction file {fpath} in existing {repro_dir}, but it was missing."
            )
            continue

        content = fpath.read_text()
        if content != expected_content:
            diff = list(
                difflib.unified_diff(
                    expected_content.splitlines(),
                    content.splitlines(),
                    fromfile="expected",
                    tofile="actual",
                    lineterm="",
                )
            )
            if fpath.name == LINUX_CONFIG_FILENAME:
                if len(diff) > MAX_CONFIG_DIFF_LINES:
                    errors.append(
                        f"File {fpath} differs from expected contents. Diff too large to display ({len(diff)} lines)."
                    )
                else:
                    diff_lines = [color_diff_line(l) for l in diff]
                    diff_str = "\n".join(diff_lines)
                    errors.append(
                        f"File {fpath} differs from expected contents. Diff:\n{diff_str}\n"
                    )
            else:
                diff_lines = [color_diff_line(l) for l in diff]
                diff_str = "\n".join(diff_lines)
                errors.append(
                    f"File {fpath} differs from expected contents. Diff:\n{diff_str}\n"
                )

    if errors:
        raise ReproductionError("\n".join(errors))

    log(f"[ok] Reproduction package {repro_dir} is valid.")


def _parse_log_timestamp(line: str) -> datetime | None:
    m = LOG_TIMESTAMP_RE.match(line)
    return datetime.strptime(m.group(1), "%Y/%m/%d %H:%M:%S") if m else None


def elapsed_hours_from_log(log_file: Path) -> float:
    """
    Time between the first and last timestamped lines of syz-manager.log, in hours.
    Assumes the log has not been resumed before (see RESUMED_FLAG_FILENAME).
    """
    first = None
    with open(log_file, errors="replace") as f:
        for line in f:
            first = _parse_log_timestamp(line)
            if first is not None:
                break
    if first is None:
        return 0.0

    last = None
    with open(log_file, "rb") as f:
        size = f.seek(0, os.SEEK_END)
        chunk = 1 << 16
        # Grow the tail window until it contains a timestamped line
        while last is None:
            start = max(size - chunk, 0)
            f.seek(start)
            lines = f.read(size - start).decode(errors="replace").splitlines()
            if start > 0:
                lines = lines[1:]  # first line may be cut in the middle
            for line in reversed(lines):
                last = _parse_log_timestamp(line)
                if last is not None:
                    break
            if start == 0:
                break
            chunk *= 4

    return (last - first).total_seconds() / 3600 if last else 0.0


def count_finished_campaigns(work_dir: Path) -> int:
    """Number of archived campaigns (previous_run_X directories)."""
    return sum(
        1
        for d in work_dir.iterdir()
        if d.is_dir() and d.name.startswith("previous_run_")
    )


def get_next_archive_dir(work_dir: Path) -> Path:
    """Find the next available previous_run_X directory safely."""
    previous_run_dirs = [
        d
        for d in work_dir.iterdir()
        if d.is_dir() and d.name.startswith("previous_run_")
    ]

    nums = []
    for d in previous_run_dirs:
        parts = d.name.split("_")
        if len(parts) != 3 or parts[0] != "previous" or parts[1] != "run":
            raise ReproductionError(
                f"Found irregularly named archive directory: {d.name}"
            )

        num_str = parts[2]
        if not num_str.isdigit():
            raise ReproductionError(
                f"Archive directory number is not an integer: {d.name}"
            )

        nums.append(int(num_str))

    next_idx = max(nums) + 1 if nums else 0
    return work_dir / f"previous_run_{next_idx}"


def archive_previous_run(work_dir: Path):
    """
    Move existing corpus.db and syz-manager.log to a previous_run_X directory, and zip the log.
    """
    corpus = work_dir / CORPUS_FILENAME
    log_file = work_dir / SYZ_MANAGER_LOG_FILENAME
    (work_dir / RESUMED_FLAG_FILENAME).unlink(missing_ok=True)

    if not corpus.exists() and not log_file.exists():
        return

    old_dir = get_next_archive_dir(work_dir)
    old_dir.mkdir(parents=False, exist_ok=True)

    if corpus.exists():
        new_corpus = old_dir / CORPUS_FILENAME
        os.rename(corpus, new_corpus)
        log(f"[ok] moved {corpus.name} to {old_dir.name}")

    if log_file.exists():
        new_log = old_dir / SYZ_MANAGER_LOG_FILENAME
        os.rename(log_file, new_log)
        log(f"[ok] moved {log_file.name} to {old_dir.name}")

        # Wait for gzip to finish before continuing
        log(f"[info] zipping {new_log}...")
        subprocess.run(["gzip", str(new_log)], check=True)
        log(f"[ok] zipped {new_log.name}.gz")


def handle_existing_corpus(work_dir: Path):
    corpus = work_dir / CORPUS_FILENAME
    if not corpus.exists():
        return

    log(
        f"The directory {work_dir} already has a corpus.db file. Would you like to continue fuzzing from this run?"
    )
    reuse = prompt_for_confirm()

    if reuse:
        return
    else:
        archive_previous_run(work_dir)
        return


def write_repro_files(repro_dir: Path, expected_files: dict[Path, str]):
    """
    Write reproduction package files into repro_dir.
    """
    for fpath, content in expected_files.items():
        fpath.write_text(content)
        log(f"[write] {fpath} ({len(content)} bytes)")

    log(
        f"[ok] Working tree {repro_dir.parent} created with fresh reproduction package."
    )


def run_syz_manager(
    syzkaller_src: Path,
    cfg_path: Path,
    log_file: Path,
    verbosity: int,
    run_hours: float | None,
    resume: bool = False,
):
    """Run syz-manager with the given config and verbosity level, redirecting output with tee."""
    syz_manager_bin = syzkaller_src.joinpath(*SYZ_MANAGER_BIN_RELATIVE_PATH)
    if not syz_manager_bin.exists():
        raise ConfigurationError(
            f"Expected syz-manager binary at {syz_manager_bin}, but it was missing. Forgot to compile?"
        )

    if run_hours is not None:
        candidate = log_file
    else:
        # If log_file exists, append an increasing number to the filename
        base = log_file.stem
        ext = log_file.suffix
        parent = log_file.parent
        candidate = log_file
        counter = 1
        while candidate.exists():
            candidate = parent / f"{base}_{counter}{ext}"
            counter += 1

    tee_flags = "-a " if resume else ""
    cmd = f"{syz_manager_bin} -vv {verbosity} -config {cfg_path} 2>&1 | tee {tee_flags}{candidate}"
    log(f"running {cmd}")

    # Start the process in its own process group so we can reliably kill its whole tree
    proc = subprocess.Popen(["bash", "-c", cmd], preexec_fn=os.setpgrp)

    try:
        if run_hours is not None:
            try:
                proc.wait(timeout=run_hours * 3600)
            except subprocess.TimeoutExpired:
                log(
                    f"\n[info] Campaign run time of {run_hours} hours reached. Terminating syz-manager..."
                )
                # Send SIGTERM to gracefully terminate syz-manager and children
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait()
        else:
            proc.wait()
    except KeyboardInterrupt:
        log("\n[info] Received KeyboardInterrupt, stopping syz-manager gracefully...")
        os.killpg(proc.pid, signal.SIGINT)
        proc.wait()
        raise


def main():
    args = parse_args()

    linux_src = args.linux_src
    syzkaller_src = args.syzkaller_src

    required_keys = []
    if linux_src is None:
        required_keys.append("linux_src")
    if syzkaller_src is None:
        required_keys.append("syzkaller_src")

    if required_keys:
        config = load_config(Path(args.config), required_keys=required_keys)
        if not linux_src:
            linux_src = config["linux_src"]
        if not syzkaller_src:
            syzkaller_src = config["syzkaller_src"]

        if not confirm_paths(config):
            log("Operation cancelled by user")
            sys.exit(0)

    work_dir = Path(args.work_name).resolve()

    if args.resume and args.run_hours is None:
        raise ConfigurationError("--resume requires --run-hours")

    if args.resume:
        if (work_dir / RESUMED_FLAG_FILENAME).exists():
            raise ConfigurationError(
                f"The current campaign in {work_dir} was already resumed once; "
                "its elapsed time can no longer be derived from the log."
            )
        if not (work_dir / SYZ_MANAGER_LOG_FILENAME).exists():
            raise ConfigurationError(
                f"--resume given but {work_dir / SYZ_MANAGER_LOG_FILENAME} does not exist."
            )
    elif args.run_hours is not None:
        if (work_dir / CORPUS_FILENAME).exists() or (
            work_dir / SYZ_MANAGER_LOG_FILENAME
        ).exists():
            raise ConfigurationError(
                f"Working directory {work_dir} already contains {CORPUS_FILENAME} or {SYZ_MANAGER_LOG_FILENAME}. "
                "When using --run-hours, the initial state must be clean."
            )

    repro_dir = work_dir / REPRO_PACKAGE_DIRNAME
    real_cfg = repro_dir / REAL_CFG_FILENAME
    linux_config_file = repro_dir / LINUX_CONFIG_FILENAME
    linux_commit_file = repro_dir / LINUX_COMMIT_FILENAME
    syzkaller_commit_file = repro_dir / SYZKALLER_COMMIT_FILENAME

    # Build expected contents
    expected_real_cfg = copy_and_modify_cfg(
        Path(args.cfg_template), work_dir, Path(syzkaller_src), Path(linux_src)
    )
    expected_linux_config = get_linux_config(Path(linux_src))
    expected_linux_commit = get_linux_history_info(Path(linux_src))
    expected_syzkaller_commit = get_syzkaller_history_info(Path(syzkaller_src))

    expected_files: dict[Path, str] = {
        real_cfg: expected_real_cfg,
        linux_config_file: expected_linux_config,
        linux_commit_file: json.dumps(expected_linux_commit, indent=4),
        syzkaller_commit_file: json.dumps(expected_syzkaller_commit, indent=4),
    }

    campaign_count = 0

    if not work_dir.exists():
        work_dir.mkdir(parents=False)

    existing_repro, existing_corpus = get_existing_work_dir(work_dir)

    if existing_repro is not None:
        check_repro_package(existing_repro, expected_files)
    else:
        create_repro_dir(
            linux_src,
            syzkaller_src,
            repro_dir,
            expected_linux_commit,
            expected_syzkaller_commit,
            expected_files,
        )

    if args.run_hours is None and existing_corpus is not None:
        handle_existing_corpus(work_dir)

    resuming = args.resume
    run_hours = args.run_hours
    if resuming:
        campaign_count = count_finished_campaigns(work_dir)
        if args.N_runs is not None and campaign_count >= args.N_runs:
            raise ConfigurationError(
                f"{campaign_count} campaigns already finished in {work_dir}; "
                f"nothing left to resume for --N-runs {args.N_runs}."
            )
        elapsed = elapsed_hours_from_log(work_dir / SYZ_MANAGER_LOG_FILENAME)
        (work_dir / RESUMED_FLAG_FILENAME).touch()
        log(
            f"[info] Resuming campaign {campaign_count + 1}: {elapsed:.3f}h of {args.run_hours}h already elapsed."
        )

    while True:
        campaign_count += 1

        if campaign_count > 1 and not resuming:
            archive_previous_run(work_dir)

        log_file = work_dir / SYZ_MANAGER_LOG_FILENAME

        if resuming:
            run_hours = max(args.run_hours - elapsed, 0.0)

        if run_hours > 0 or not resuming:
            run_syz_manager(
                Path(syzkaller_src),
                real_cfg,
                log_file,
                args.verbosity,
                run_hours,
                resume=resuming,
            )
        else:
            log("[info] Interrupted campaign had already reached its run time.")
        resuming = False
        run_hours = args.run_hours

        if args.run_hours is None:
            break

        if args.N_runs is not None and campaign_count >= args.N_runs:
            log(
                f"\n[info] Completed the desired amount of campaigns ({args.N_runs}). Exiting."
            )
            break


def create_repro_dir(
    linux_src: str,
    syzkaller_src: str,
    repro_dir: Path,
    expected_linux_commit: dict[str, str | None],
    expected_syzkaller_commit: dict[str, str | None],
    expected_files: dict[Path, str],
):
    repro_dir.mkdir(parents=False)
    create_patch_from_info(
        expected_linux_commit, repro_dir / LINUX_DIFF_FILENAME, Path(linux_src)
    )
    create_patch_from_info(
        expected_syzkaller_commit,
        repro_dir / SYZKALLER_DIFF_FILENAME,
        Path(syzkaller_src),
    )
    write_repro_files(repro_dir, expected_files)

    # Write the README outside of expected_files so different script versions
    # don't invalidate existing reproduction packages during check_repro_package.
    script_commit, script_remote = get_script_repo_info()
    readme_content = (
        "# Reproduction Package\n\n"
        f"This directory was automatically generated by `invoke-syz-manager.py`, "
        f"which is hosted at {script_remote} (commit {script_commit}).\n"
    )
    readme_path = repro_dir / README_FILENAME
    readme_path.write_text(readme_content)
    log(f"[write] {readme_path} ({len(readme_content)} bytes)")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReproductionError as e:
        log(
            f"[ReproductionError]: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except ConfigurationError as e:
        log(
            f"[ConfigurationError]: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
