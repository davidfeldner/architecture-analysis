import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor


from pathlib import Path
from pyvis.network import Network

import matplotlib

import git
import os
from collections import defaultdict

from evolution_metrics import module_churn

matplotlib.use("TkAgg")

CODE_ROOT_FOLDER = "src/server/src/"


def get_source(remote="https://github.com/immich-app/immich.git"):
    git.Repo.clone_from(remote, "src")


def add_node(net, name, color, label=None, size=None, title=None):
    font = {
        "color": color,
        "background": "#eef2ff",
        "strokeWidth": 0.2,
        "strokeColor": "#ffffff",
    }
    if size is not None:
        font["size"] = size

    net.add_node(
        name,
        label=label or name,
        color=color,
        shape="box",
        size=size,
        value=size,
        title=title,
        font=font,
    )


def filter_libraries(content):
    if not content.startswith("src/"):
        return False

    return True


def filter_migrations(content):
    if content.startswith("src/schema/migrations"):
        return False

    return True


def churn_size(module, churn):
    max_churn = max(churn.values(), default=0)

    return 1 + int(40 * churn.get(module, 0) / (max_churn*0.8))


def set_barnes_hut(net):
    net.set_options("""
    var options = {
        "physics": {
            "enabled": true,
            "barnesHut": {
                "gravitationalConstant": -1800,
                "springLength": 220,
                "springConstant": 0.02,
                "damping": 0.55
            },
            "solver": "barnesHut"
        }
    }
    """)


def dependencies_digraph(code_root_folder, filter_lib=True, filter_mig=True):
    net = Network(directed=True, height="750px", width="100%")

    files = Path(code_root_folder).rglob("*.ts")
    churn = module_churn("src")

    references = defaultdict(lambda: defaultdict(int))
    for file in files:
        file_path = str(file)

        source_module = module_name_from_file_path(file_path)

        if (
            (filter_lib and not filter_libraries(source_module)) or
            (filter_mig and not filter_migrations(source_module))
        ):
            continue

        add_node(
            net,
            source_module,
            "#2255aa",
            size=churn_size(source_module, churn),
            title=f"churn: {churn.get(source_module, 0)}",
        )

        for target_module in imports_from_file(file_path):
            if (
                (filter_lib and not filter_libraries(target_module)) or
                (filter_mig and not filter_migrations(target_module))
            ):
                continue

            references[source_module][target_module] += 1

    for s in references:
        for t in references[s]:
            if s == t:
                continue
            if t not in references:
                add_node(
                    net,
                    t,
                    "#2255aa",
                    size=churn_size(t, churn),
                    title=f"churn: {churn.get(t, 0)}",
                )
            net.add_edge(
                s,
                t,
                label=str(references[s][t])
            )

    set_barnes_hut(net)

    return net


def dependencies_digraph_hierarchical(code_root_folder, filter_lib=True, filter_mig=True, show_files=False, min_weight=0, physics=False):
    net = Network(directed=True, height="750px", width="100%")
    if not physics:
        net.set_options("""
        var options = {
            "physics": {
                "enabled": false
            },
            "edges": {
                "smooth": {
                    "enabled": false
                }
            }
        }
        """)

    files = Path(code_root_folder).rglob("*.ts")

    references = defaultdict(lambda: defaultdict(int))
    for file in files:
        file_path = str(file)

        source_module = module_name_from_file_path(file_path)

        if (
            (filter_lib and not filter_libraries(source_module)) or
            (filter_mig and not filter_migrations(source_module))
        ):
            continue

        depth = 2
        source_node, source_label, source_color = hierarchical_module(
            source_module, depth, show_files)
        if source_node is None:
            continue
        add_node(net, source_node, source_color, source_label)

        for target_module in imports_from_file(file_path):
            if (
                (filter_lib and not filter_libraries(target_module)) or
                (filter_mig and not filter_migrations(target_module))
            ):
                continue

            target_node, target_label, target_color = hierarchical_module(
                target_module, depth, show_files)
            if target_node is None:
                continue
            add_node(net, target_node, target_color, target_label)
            references[source_node][target_node] += 1

    for s in references:
        for t in references[s]:
            if s == t:
                continue
            if t not in references:
                target_color = "#44bb44" if t.startswith(
                    "folder:") else "#2255aa"
                add_node(net, t, target_color, t.split(":", 1)[1])
            weight = references[s][t]
            if weight < min_weight:
                continue
            net.add_edge(
                s,
                t,
                label=str(references[s][t]),
                width=0.5 + weight * 0.1,
            )
    if physics:
        net.show_buttons()
    return net


def hierarchical_module(module, depth, show_files=True):
    module_parts = module.split("/")

    module_path = Path(CODE_ROOT_FOLDER).parent / module
    is_index_import = (module_path / "index.ts").is_file()

    if is_index_import or len(module_parts) > depth:
        folder = "/".join(module_parts[:depth])
        return "folder:" + folder, folder[4:], "#44bb44"

    if not show_files:
        return None, None, None

    return "file:" + module, module.replace[4:], "#2255aa"


def module_name_from_file_path(full_path):

    # File paths are under src/server/src, but imports start at src/.
    if full_path.startswith(CODE_ROOT_FOLDER):
        file_path = "src/" + full_path[len(CODE_ROOT_FOLDER):]
    else:
        file_path = full_path

    module = file_path.replace(".ts", "")

    # References to a folder by default reads index.ts,
    # so we remove it so it matches the import
    module_parts = module.split("/")
    is_index = module_parts[-1] == "index"
    if is_index:
        module_parts.pop(-1)
        module = "/".join(module_parts)

    return module


TS_LANGUAGE = Language(ts_typescript.language_typescript())
parser = Parser(TS_LANGUAGE)


def applyFilters(content):
    if content.startswith("schema/migrations"):
        return False

    return True


def imports_from_file(filename: str):

    with open(filename, "rb") as f:
        source = f.read()

    tree = parser.parse(source)
    root = tree.root_node

    query = Query(
        TS_LANGUAGE,
        """
    (import_statement
    source: (string (string_fragment) @source))
    """,
    )

    cursor = QueryCursor(query)
    captures = cursor.captures(root)

    res = []
    if "source" not in captures:
        return []
    for node in captures["source"]:
        content = node.text.decode()
        if applyFilters(content):
            res.append(content)

    return res


def main():
    if not os.path.exists(CODE_ROOT_FOLDER):
        get_source()
    net = dependencies_digraph_hierarchical(CODE_ROOT_FOLDER)
    net.show("graph.html", notebook=False)


if __name__ == "__main__":
    main()
