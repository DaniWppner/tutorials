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
LINUX_COMMIT_FILENAME = "linux_commit_difference.json"
LINUX_DIFF_FILENAME = "linux_diff_from_ancestor.patch"
SYZKALLER_COMMIT_FILENAME = "syzkaller_commit_difference.json"
SYZKALLER_DIFF_FILENAME = "syzkaller_diff_from_ancestor.patch"
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


def load_config(config_path: Path, required_keys: list[str]) -> dict[str, str]:
    """
    Load configuration from config.json file in the current working directory.
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ConfigurationError(f"Missing required keys in config file: {missing_keys}")
            return config
    except FileNotFoundError:
        raise ConfigurationError(f"Configuration file not found at {config_path}")
    except json.JSONDecodeError:
        raise ConfigurationError(f"Invalid JSON in configuration file {config_path}")

def confirm_paths(required_keys: dict[str,Path]) -> bool:
    """
    Ask user to confirm the paths that will be used.
    """
    def prompt_for_confirm() -> bool:
        while True:
            response = input("\nDo you want to continue? [y/N]: ").lower()
            if response in ['y', 'yes']:
                return True
            if response in ['', 'n', 'no']:
                return False
            print("Please answer 'y' or 'n'")

    res = True
    for key, val in required_keys.items():
        print(f"The following {key} source path will be used:\n {str(val)}")
        res = res and prompt_for_confirm()
    return res

def parse_args():
    parser = argparse.ArgumentParser(
        description="Automate execution of syz-manager with a reproducible working tree."
    )
    parser.add_argument("--linux-src", help="Path to the Linux source tree (overrides config file)")
    parser.add_argument("--cfg-template", required=True, help="Path to the syzkaller .cfg template")
    parser.add_argument("--syzkaller-src", help="Path to the syzkaller source tree (overrides config file)")
    parser.add_argument("--work-name", required=True, help="Name to use for the working tree")
    parser.add_argument("--config", default="config.json", help="Path to the configuration file (default: config.json)")
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

def get_syzkaller_history_info(repo_source_root: Path) -> dict[str, str|None]:
    """
    Return commit info up to the local HEAD from the syzkaller repo.
    For syzkaller we assume we are on a branch that is tracked remotely.
    """
    branch = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "rev-parse", "--abbrev-ref", "HEAD"], text=True
    ).strip()

    remote_branch = get_remote(repo_source_root, branch)
    if remote_branch is None:
        raise ConfigurationError(f"Current branch {branch} in syzkaller repo at {repo_source_root} has no upstream.")

    remote_url = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "remote", "get-url", remote_branch], text=True
    ).strip()

    remote_head = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "rev-parse", "@{u}"], text=True
    ).strip()
    remote_head_msg = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "log", "-1", "@{u}", "--pretty=%s"], text=True
    ).strip()

    untracked_commits = commits_to_head(repo_source_root, remote_head)

    ancestor_info = {
        'hash': remote_head,
        'message': remote_head_msg,
        'branch': branch,
        'upstream': remote_url,
    }
    difference = {
        'distance': len(untracked_commits),
        'commits': untracked_commits
    }
    return {"last_ancestor": ancestor_info,
            "difference": difference}

def get_linux_history_info(repo_source_root: Path) -> dict[str, str|None]:
    """
    Return commit info up to the local HEAD from the Linux repo.
    For Linux we report the difference from the closest tag.
    """

    last_ancestor = get_last_tag(repo_source_root)
    untracked_commits = commits_to_head(repo_source_root, last_ancestor['commit_hash'])
    ancestor_info = {
        'hash': last_ancestor['commit_hash'],
        'message': last_ancestor['commit_message'],
        'tag': last_ancestor['tag']
    }
    difference = {
        'distance': len(untracked_commits),
        'commits': untracked_commits
    }

    return {"last_ancestor": ancestor_info,
            "difference": difference}

def get_remote(repo_source_root: Path, branch: str) -> str|None:
    '''
    Return the remote name for the given branch, or None if it has no remote.
    '''
    try:
        remote_name = subprocess.check_output(
            ["git", "-C", str(repo_source_root), "config", f"branch.{branch}.remote"], text=True
        ).strip()
    except subprocess.CalledProcessError:
        remote_name = None
    return remote_name

def commits_to_head(repo_source_root: Path, ancestor_hash: str) -> list[dict[str, str]]:
    """
    Return list of commits from ancestor_hash (exclusive) to HEAD (inclusive).
    """
    commit_lines = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "log", f"{ancestor_hash}..HEAD", "--pretty=%H,%s"], text=True
    ).strip().splitlines()
    
    commits = []
    for line in commit_lines:
        commit_hash, commit_msg = line.split(',', 1)
        commits.append({'hash': commit_hash, 'message': commit_msg})
    return commits

def get_last_tag(repo_source_root: Path) -> dict[str, str]:
    '''
    Return the closest tag, and the commit hash and message at that tag.
    '''
    tag = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "describe"], text=True
    ).strip().split('-')[0]
        
    commit_hash_and_message = subprocess.check_output(
        ["git", "-C", str(repo_source_root), "log", "-1", "--pretty=%H,%s", f"tags/{tag}"], text=True
    ).strip()
    commit_hash, commit_msg = commit_hash_and_message.split(',', 1)

    return {
        "commit_hash": commit_hash,
        "tag": tag,
        "commit_message": commit_msg,
    }

def create_patch_from_info(history_info: dict[str, str], output_path: Path, repo_source_root: Path):
    """
    Create a patch file from the ancestor to HEAD using git diff
    """
    if history_info['difference']['distance'] == 0:
        print(f"[info] No unpushed commits in repo at {repo_source_root}, skipping patch creation.")
        return
    else:
        ancestor_hash = history_info['last_ancestor']['hash']
        with open(output_path, 'w') as f:
            subprocess.run(
                ["git", "-C", str(repo_source_root), "diff", f"{ancestor_hash}..HEAD"],
                stdout=f
            )
        print(f"[write] create git patch at {output_path}")
    
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


def write_repro_files(repro_dir: Path, expected_files: dict[Path, str]):
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

    linux_src = args.linux_src
    syzkaller_src = args.syzkaller_src

    required_keys = []
    if linux_src is None:
        required_keys.append('linux_src')
    if syzkaller_src is None:
        required_keys.append('syzkaller_src')

    if required_keys:
        config = load_config(Path(args.config), required_keys=required_keys)
        if not linux_src:
            linux_src = config['linux_src']
        if not syzkaller_src:
            syzkaller_src = config['syzkaller_src']

        if not confirm_paths(config):
            print("Operation cancelled by user")
            sys.exit(0)

    work_dir = Path(args.work_name).resolve()
    repro_dir = work_dir / REPRO_PACKAGE_DIRNAME
    real_cfg = repro_dir / REAL_CFG_FILENAME
    linux_config_file = repro_dir / LINUX_CONFIG_FILENAME
    linux_commit_file = repro_dir / LINUX_COMMIT_FILENAME
    syzkaller_commit_file = repro_dir / SYZKALLER_COMMIT_FILENAME

    # Build expected contents
    expected_real_cfg = copy_and_modify_cfg(
        Path(args.cfg_template),
        work_dir,
        Path(syzkaller_src),
        Path(linux_src)
    )
    expected_linux_config = get_linux_config(Path(linux_src))
    expected_linux_commit = get_linux_history_info(Path(linux_src))
    expected_syzkaller_commit = get_syzkaller_history_info(Path(syzkaller_src))

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
        create_patch_from_info(expected_linux_commit, repro_dir / LINUX_DIFF_FILENAME, Path(linux_src))
        create_patch_from_info(expected_syzkaller_commit, repro_dir / SYZKALLER_DIFF_FILENAME, Path(syzkaller_src))
        write_repro_files(repro_dir, expected_files)


    log_file = work_dir / SYZ_MANAGER_LOG_FILENAME
    run_syz_manager(Path(syzkaller_src), real_cfg, log_file)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except ReproductionError as e:
        print(f"[ReproductionError] workdir already exists but there's a mismatch in the expected reproduction package: \n{e}", file=sys.stderr)
        sys.exit(1)
    except ConfigurationError as e:
        print(f"[ConfigurationError] some files expected to be able to run syzkaller are missing or incorrect: \n{e}", file=sys.stderr)
        sys.exit(1)
