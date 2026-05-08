import matplotlib.pyplot as plt
from numpy import add, shape
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor


from pathlib import Path
import networkx as nx
from pyvis.network import Network

import matplotlib

import git
import os
from collections import defaultdict

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


def make_graph():
    net = Network(directed=True, height="750px", width="100%")

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
    return net


def draw_graph(net):

    # net.from_nx(G)
    # net.show_buttons()
    # net.barnes_hut(overlap=0.5, spring_strength=0.01, spring_length=500, gravity=-8000)
    net.show("graph.html", notebook=False)


def add_node(net, name, color):
    net.add_node(
        name,
        color=color,
        shape="box",
        # size=0,
        # mass=1,
        font={
            # "size": 40,
            "color": color,
            "background": "#eef2ff",
            "strokeWidth": 0.2,
            "strokeColor": "#ffffff",
        },
    )


def dependencies_digraph(net, code_root_folder):
    files = Path(code_root_folder).rglob("*.ts")
    min_weight = 0

    dirs = set()
    references = defaultdict(lambda: defaultdict(int))
    for file in files:
        file_path = str(file)

        source_module = module_name_from_file_path(file_path)

        if not applyFilters(source_module):
            continue

        depth = 2
        source_parts = source_module.split("/")
        if source_parts[-1] == "index":
            source_parts.pop(-1)
            source_module = "/".join(source_parts)

        if len(source_parts) <= depth or source_module.startswith("@"):
            # add_node(net, source_module, "#2255aa")
            pass
        else:
            source_module = "/".join(source_parts[:depth]) + "/"
            add_node(net, source_module, "#44bb44")

        for target_module in imports_from_file(file_path):
            print(net.nodes)

            target_parts = target_module.split("/")
            if len(target_parts) > depth:
                target_module = "/".join(target_parts[:depth]) + "/"
            references[source_module][target_module] += 1

        # print(module_name + "=>" + each + ".")
    print(references)
    for s in references:
        for t in references[s]:
            if s == t:
                continue
            print(s, " : ", t)
            try:
                weight = references[s][t]
                if weight < min_weight:
                    continue
                net.add_edge(
                    s,
                    t,
                    label=str(references[s][t]),
                    # font={"size": 20},
                    # width=0.5 + weight * 0.2,
                    # arrows={
                    #     "to": {
                    #         "enabled": True,
                    #         "scaleFactor": 0.5,  # keeps arrowhead small regardless of width
                    #     }
                    # },
                )
            except:
                pass


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
    net = make_graph()
    if not os.path.exists(CODE_ROOT_FOLDER):
        get_source()
    dependencies_digraph(net, CODE_ROOT_FOLDER)
    draw_graph(net)


if __name__ == "__main__":
    main()
