from collections import defaultdict
import json
from pathlib import Path

from pydriller import ModificationType, Repository


def commit_counts(repo_dir, path_prefix="server/src/", extension=".ts", cache_file="churn.json"):
    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    counts = {}

    for commit in Repository(repo_dir).traverse_commits():
        for modification in commit.modified_files:
            new_path = modification.new_path
            old_path = modification.old_path

            try:
                if modification.change_type == ModificationType.RENAME:
                    counts[new_path] = counts.get(old_path, 0) + 1
                    counts.pop(old_path, None)

                elif modification.change_type == ModificationType.DELETE:
                    counts.pop(old_path, None)

                elif modification.change_type == ModificationType.ADD:
                    counts[new_path] = 1

                else:
                    counts[old_path] += 1

            except Exception:
                pass

    result = {
        path: count
        for path, count in counts.items()
        if path and path.startswith(path_prefix) and path.endswith(extension)
    }

    with open(cache_path, "w") as f:
        json.dump(result, f, sort_keys=True)

    return result


def module_churn(repo_dir, source_root="server/src/", import_root="src/", cache_file="module_churn.json"):
    cache_path = Path(cache_file)
    if cache_path.exists():
        with open(cache_path) as f:
            return json.load(f)

    churn = defaultdict(int)

    for path, count in commit_counts(repo_dir, source_root).items():
        module = import_root + path[len(source_root):]
        module = module.removesuffix(".ts").removesuffix("/index")
        churn[module] += count

    result = dict(churn)

    with open(cache_path, "w") as f:
        json.dump(result, f, sort_keys=True)

    return result
