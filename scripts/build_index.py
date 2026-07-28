"""Build the retrieval index over companion_docs/. Run once, and again after
any edit to the companion documents."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import rag  # noqa: E402

if __name__ == "__main__":
    n = rag.build_index()
    print(f"Indexed {n} chunks from companion_docs/ -> data/companion_index.npz")
