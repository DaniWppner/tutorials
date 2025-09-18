#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
from pathlib import Path


class ReproductionError(Exception):
    """Raised when the reproduction package is invalid or inconsistent."""
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


def copy_and_modify_cfg(cfg_template: Path, work_dir: Path) -> str:
    """Return expected contents for real.cfg after copying/modifying."""
    raise NotImplementedError


def get_linux_config(linux_src: Path) -> str:
    """Return contents of the Linux .config file."""
    raise NotImplementedError


def get_linux_commit(linux_src: Path) -> str:
    """Return last commit id + message of the Linux tree."""
    raise NotImplementedError


def get_syzkaller_commit(syzkaller_src: Path) -> str:
    """Return last commit id + branch name of the Syzkaller tree."""
    raise NotImplementedError


def check_working_tree(work_dir: Path, expected_files: dict[Path, str]):
    """
    Check if the working tree exists and validate reproduction package contents.
    """
    repro_dir = work_dir / "repro_package"
    if not repro_dir.exists():
        raise ReproductionError(
            f"Directory with name {work_dir} already exists but reproduction package is missing. "
            f"You should probably choose a different workdir name."
        )

    errors = []
    for fpath, expected_content in expected_files.items():
        if not fpath.exists():
            errors.append(f"Expected reproduction file {fpath} in existing {repro_dir}, but it was missing.")
            continue

        content = fpath.read_text()
        if content != expected_content:
            errors.append(
                f"Existing reproduction file in {fpath} doesn't match expected contents.\n"
            )

    if errors:
        raise ReproductionError("\n".join(errors))

    print(f"[ok] Working tree {work_dir} contains valid existing reproduction package.")

def write_repro_package(repro_dir: Path, expected_files: dict[Path, str]):
    """
    Write reproduction package files into repro_dir.
    """
    for fpath, content in expected_files.items():
        fpath.write_text(content)
        print(f"[ok] Write reproduction file: {fpath} ({len(content)} bytes)")


def run_syz_manager(syzkaller_src: Path, cfg_path: Path, log_file: Path):
    """Run syz-manager with -vv 10 and the given config, redirecting output with tee."""
    syz_manager_bin = syzkaller_src / "bin" / "syz-manager"
    if not syz_manager_bin.exists():
        raise RuntimeError(f"Expected syz-manager binary at {syz_manager_bin}, but it was missing. Forgot to compile?")

    print(f"running {cmd}")
    cmd = f"{syz_manager_bin} -vv 10 -config {cfg_path} 2>&1 | tee {log_file}"

    # Hand over execution: replace current process with syz-manager+tee
    os.execvp("bash", ["bash", "-c", cmd])



def main():
    args = parse_args()

    # Resolve working directory
    work_dir = Path(args.work_name).resolve()
    repro_dir = work_dir / "repro_package"

    # Paths of reproduction package files
    real_cfg = repro_dir / "real.cfg"
    linux_config_file = repro_dir / "linux.config"
    linux_commit_file = repro_dir / "linux_commit.txt"
    syzkaller_commit_file = repro_dir / "syzkaller_commit.txt"

    # Build expected contents using template functions
    expected_real_cfg = copy_and_modify_cfg(Path(args.cfg_template), work_dir)
    expected_linux_config = get_linux_config(Path(args.linux_src))
    expected_linux_commit = get_linux_commit(Path(args.linux_src))
    expected_syzkaller_commit = get_syzkaller_commit(Path(args.syzkaller_src))

    expected_files = {
        real_cfg: expected_real_cfg,
        linux_config_file: expected_linux_config,
        linux_commit_file: expected_linux_commit,
        syzkaller_commit_file: expected_syzkaller_commit,
    }

    if work_dir.exists():
        check_working_tree(work_dir, expected_files)
    else:
        work_dir.mkdir(parents=False)
        repro_dir.mkdir(parents=False)
        write_repro_package(repro_dir, expected_files)

    log_file = work_dir / "syz-manager.log"
    run_syz_manager(Path(args.syzkaller_src), real_cfg, log_file)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReproductionError as e:
        print(f"[ReproductionError] workdir already exists but there's a mismatch in the expected reproduction package: {e}", file=sys.stderr)
        sys.exit(1)
