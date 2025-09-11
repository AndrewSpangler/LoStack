import os

def make_tree(path, depth=0):
    if depth == 0:
        print(os.path.abspath(path))
    else:
        print("    " * (depth - 1) + "📂 " + os.path.basename(path))

    for entry in os.scandir(path):
        if entry.is_dir():
            if "svg" in entry.path or "bootstrap" in entry.path:
                continue
            make_tree(entry.path, depth + 1)
        else:
            print("    " * depth + "📄 " + entry.name)

if __name__ == "__main__":
    make_tree(".")
