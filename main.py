
import matplotlib.pyplot as plt
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor


from pathlib import Path
import networkx as nx

import matplotlib
matplotlib.use("TkAgg")

CODE_ROOT_FOLDER = "../immich/server/src"


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
    plt.figure(figsize=size)
    pos = nx.spring_layout(G, scale=1)
    nx.draw(G, font_color="gray", pos=pos, **args)
    plt.show()


def dependencies_digraph(code_root_folder):
    files = Path(code_root_folder).rglob("*.ts")

    G = nx.DiGraph()

    for file in files:
        file_path = str(file)

        source_module = module_name_from_file_path(file_path)

        if source_module not in G.nodes:
            G.add_node(source_module)

        for target_module in imports_from_file(file_path):

            G.add_edge(source_module, target_module)
            # print(module_name + "=>" + each + ".")

    return G


def module_name_from_file_path(full_path):
    # e.g. ../core/model/user.py -> zeeguu.core.model.user

    file_name = full_path[len(CODE_ROOT_FOLDER):].replace(".ts", "")
    return file_name


TS_LANGUAGE = Language(ts_typescript.language_typescript())
parser = Parser(TS_LANGUAGE)


def imports_from_file(filename: str):

    with open(filename, "rb") as f:
        source = f.read()

    tree = parser.parse(source)
    root = tree.root_node

    for child in root.children:
        print(child.type)

    query = Query(TS_LANGUAGE, """
    (import_statement
    source: (string (string_fragment) @source))
    """)

    cursor = QueryCursor(query)
    captures = cursor.captures(root)

    res = []
    if "source" not in captures:
        return []
    for node in captures["source"]:
        print(node.text.decode())
        res.append(node.text.decode())

    return res


def main():
    DG = dependencies_digraph(CODE_ROOT_FOLDER)
    draw_graph(DG, (40, 40), with_labels=True)


if __name__ == "__main__":
    main()
