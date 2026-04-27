import matplotlib.pyplot as plt
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor


from pathlib import Path
import networkx as nx
from pyvis.network import Network

import matplotlib

import git
import os

matplotlib.use("TkAgg")

CODE_ROOT_FOLDER = "src/server/src/"


def get_source(remote="https://github.com/immich-app/immich.git"):
    git.Repo.clone_from(remote, "src")


def dependencies_graph(code_root_folder):
    files = Path(code_root_folder).rglob("*.ts")

    G = nx.Graph()

    for file in files:
        file_path = str(file)

        module_name = module_name_from_file_path(file_path)

        if module_name not in G.nodes:
            G.add_node(module_name)

        for each in imports_from_file(file_path):
            G.add_edge(module_name, each)

    return G


def draw_graph(G, size, **args):
    net = Network(height="750px", width="100%")

    net.from_nx(G)
    net.show_buttons(filter_=["physics"])
    net.show("graph.html", notebook=False)


def dependencies_digraph(code_root_folder):
    files = Path(code_root_folder).rglob("*.ts")

    G = nx.DiGraph()

    for file in files:
        file_path = str(file)

        source_module = module_name_from_file_path(file_path)

        if not applyFilters(source_module):
            continue

        if source_module not in G.nodes:
            G.add_node(source_module)

        for target_module in imports_from_file(file_path):

            G.add_edge(source_module, target_module)
            # print(module_name + "=>" + each + ".")

    return G


def module_name_from_file_path(full_path):
    # e.g. ../core/model/user.py -> zeeguu.core.model.user

    full_path = full_path[len(CODE_ROOT_FOLDER) - 4 :]

    file_name = full_path.replace(".ts", "")
    return file_name


TS_LANGUAGE = Language(ts_typescript.language_typescript())
parser = Parser(TS_LANGUAGE)


def applyFilters(content):
    if content.startswith("src/schema/migrations"):
        return False

    if content.startswith("@immich") or content.startswith("src"):
        return True
    return False


def imports_from_file(filename: str):

    with open(filename, "rb") as f:
        source = f.read()

    tree = parser.parse(source)
    root = tree.root_node

    # for child in root.children:
    #    print(child.type)

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
            # print(content)
            res.append(content)

    return res


def main():
    if not os.path.exists(CODE_ROOT_FOLDER):
        get_source()
    DG = dependencies_digraph(CODE_ROOT_FOLDER)
    draw_graph(DG, (40, 40), with_labels=True)


if __name__ == "__main__":
    main()
