#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
import json
from pathlib import Path
import difflib


# Constants for hardcoded paths and filenames
REPRO_PACKAGE_DIRNAME = "repro_package"
REAL_CFG_FILENAME = "syzkaller.cfg"
LINUX_CONFIG_FILENAME = ".config"
LINUX_COMMIT_FILENAME = "linux_commit.json"
SYZKALLER_COMMIT_FILENAME = "syzkaller_commit.json"
SYZ_MANAGER_LOG_FILENAME = "syz-manager.log"
SYZ_MANAGER_BIN_RELATIVE_PATH = ["bin", "syz-manager"]
BZIMAGE_RELATIVE_PATH = ["arch", "x86", "boot", "bzImage"]


def color_diff_line(line: str) -> str:
    if line.startswith('+') and not line.startswith('+++'):
        return f'\033[32m{line}\033[0m'  # Green
    elif line.startswith('-') and not line.startswith('---'):
        return f'\033[31m{line}\033[0m'  # Red
    elif line.startswith('@'):
        return f'\033[36m{line}\033[0m'  # Cyan
    else:
        return line

class ReproductionError(Exception):
    """Raised when the reproduction package is invalid or inconsistent."""
    pass

class ConfigurationError(Exception):
    pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automate execution of syz-manager with a reproducible working tree."
    )
    parser.add_argument("--linux-src", required=True, help="Path to the Linux source tree")
    parser.add_argument("--cfg-template", required=True, help="Path to the syzkaller .cfg template")
    parser.add_argument("--syzkaller-src", required=True, help="Path to the syzkaller source tree")
    parser.add_argument("--work-name", required=True, help="Name to use for the working tree")
    return parser.parse_args()


def copy_and_modify_cfg(
    cfg_template: Path,
    work_dir: Path,
    syzkaller_path: Path,
    linux_src_path: Path
) -> str:
    """
    Return expected contents for real.cfg after copying/modifying.
    """
    with open(cfg_template, 'r') as f:
        config = json.load(f)

    config["workdir"] = str(work_dir)
    config["syzkaller"] = str(syzkaller_path)
    config["kernel_src"] = str(linux_src_path)
    config["kernel_obj"] = str(linux_src_path)
    bzimage_path = Path(linux_src_path)
    for part in BZIMAGE_RELATIVE_PATH:
        bzimage_path = bzimage_path / part
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


def get_last_commit(repo_source_root: Path) -> dict[str, str]:
    """
    Return last commit info from the github repo.
    """
    commit_hash = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "rev-parse", "HEAD"], text=True
    ).strip()

    commit_msg = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "log", "-1", "--pretty=%s"], text=True
    ).strip()

    branch = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()

    remote_name = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "config", f"branch.{branch}.remote"], text=True
    ).strip()

    remote_url = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "remote", "get-url", remote_name], text=True
    ).strip()

    return {"hash": commit_hash, "message": commit_msg, "branch": branch, "remote": remote_url}



def check_working_tree(work_dir: Path, expected_files: dict[Path, str]):
    """
    Check if the working tree exists and validate reproduction package contents.
    """
    repro_dir = work_dir / REPRO_PACKAGE_DIRNAME
    if not repro_dir.exists():
        raise ReproductionError(
            f"Directory with name {work_dir} already exists but reproduction package is missing. "
            f"You should probably choose a different workdir name."
        )

    MAX_CONFIG_DIFF_LINES = 10
    errors = []

    for fpath, expected_content in expected_files.items():
        if not fpath.exists():
            errors.append(f"Expected reproduction file {fpath} in existing {repro_dir}, but it was missing.")
            continue

        content = fpath.read_text()
        if content != expected_content:
            diff = list(difflib.unified_diff(
                expected_content.splitlines(),
                content.splitlines(),
                fromfile='expected',
                tofile='actual',
                lineterm=''
            ))
            if fpath.name == LINUX_CONFIG_FILENAME:
                if len(diff) > MAX_CONFIG_DIFF_LINES:
                    errors.append(f"File {fpath} differs from expected contents. Diff too large to display ({len(diff)} lines).")
                else:
                    diff_lines = [color_diff_line(l) for l in diff]
                    diff_str = '\n'.join(diff_lines)
                    errors.append(f"File {fpath} differs from expected contents. Diff:\n{diff_str}\n")
            else:
                diff_lines = [color_diff_line(l) for l in diff]
                diff_str = '\n'.join(diff_lines)
                errors.append(f"File {fpath} differs from expected contents. Diff:\n{diff_str}\n")

    if errors:
        raise ReproductionError("\n".join(errors))

    if errors:
        raise ReproductionError("\n".join(errors))

    print(f"[ok] Working tree {work_dir} contains valid existing reproduction package.")


def write_repro_package(repro_dir: Path, expected_files: dict[Path, str]):
    """
    Write reproduction package files into repro_dir.
    """
    for fpath, content in expected_files.items():
        fpath.write_text(content)
        print(f"[write] {fpath} ({len(content)} bytes)")

    print(f"[ok] Working tree {repro_dir.parent} created with fresh reproduction package.")



def run_syz_manager(syzkaller_src: Path, cfg_path: Path, log_file: Path):
    """Run syz-manager with -vv 10 and the given config, redirecting output with tee."""
    syz_manager_bin = syzkaller_src
    for part in SYZ_MANAGER_BIN_RELATIVE_PATH:
        syz_manager_bin = syz_manager_bin / part
    if not syz_manager_bin.exists():
        raise ConfigurationError(f"Expected syz-manager binary at {syz_manager_bin}, but it was missing. Forgot to compile?")

    # If log_file exists, append an increasing number to the filename
    base = log_file.stem
    ext = log_file.suffix
    parent = log_file.parent
    candidate = log_file
    counter = 1
    while candidate.exists():
        candidate = parent / f"{base}_{counter}{ext}"
        counter += 1

    cmd = f"{syz_manager_bin} -vv 10 -config {cfg_path} 2>&1 | tee {candidate}"
    print(f"running {cmd}")

    # Hand over execution: replace current process with syz-manager+tee
    os.execvp("bash", ["bash", "-c", cmd])


def main():
    args = parse_args()

    # Resolve working directory
    work_dir = Path(args.work_name).resolve()
    repro_dir = work_dir / REPRO_PACKAGE_DIRNAME

    # Paths of reproduction package files
    real_cfg = repro_dir / REAL_CFG_FILENAME
    linux_config_file = repro_dir / LINUX_CONFIG_FILENAME
    linux_commit_file = repro_dir / LINUX_COMMIT_FILENAME
    syzkaller_commit_file = repro_dir / SYZKALLER_COMMIT_FILENAME

    # Build expected contents
    expected_real_cfg = copy_and_modify_cfg(
        Path(args.cfg_template),
        work_dir,
        Path(args.syzkaller_src),
        Path(args.linux_src)
    )
    expected_linux_config = get_linux_config(Path(args.linux_src))
    expected_linux_commit = get_last_commit(Path(args.linux_src))
    expected_syzkaller_commit = get_last_commit(Path(args.syzkaller_src))

    expected_files : dict[Path,str] = {
        real_cfg: expected_real_cfg,
        linux_config_file: expected_linux_config,
        linux_commit_file: json.dumps(expected_linux_commit, indent=4),
        syzkaller_commit_file: json.dumps(expected_syzkaller_commit, indent=4),
    }

    if work_dir.exists():
        check_working_tree(work_dir, expected_files)
    else:
        work_dir.mkdir(parents=False)
        repro_dir.mkdir(parents=False)
        write_repro_package(repro_dir, expected_files)

    log_file = work_dir / SYZ_MANAGER_LOG_FILENAME
    run_syz_manager(Path(args.syzkaller_src), real_cfg, log_file)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReproductionError as e:
        print(f"[ReproductionError] workdir already exists but there's a mismatch in the expected reproduction package: \n{e}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as e:
        print(f"[ConfigurationError] some files expected to be able to run syzkaller are missing or incorrect: \n{e}", file=sys.stderr)
        sys.exit(1)
