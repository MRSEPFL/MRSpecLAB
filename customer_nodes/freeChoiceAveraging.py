import processing.api as api
import numpy as np
import re
import os

def _parse_index_spec(spec_str, n_items):
    if not spec_str or not spec_str.strip():
        return []
    tokens = re.split(r'[,\s]+', spec_str.strip())
    out, seen = [], set()
    for tok in tokens:
        if not tok:
            continue
        t = tok.replace('-', ':')
        if ':' in t:
            parts = t.split(':')
            if len(parts) != 2:
                continue
            try:
                start = int(parts[0]); end = int(parts[1])
            except ValueError:
                continue
            lo = min(start, end) - 1
            hi = max(start, end) - 1
            for idx in range(lo, hi + 1):
                if 0 <= idx < n_items and idx not in seen:
                    seen.add(idx); out.append(idx)
        else:
            try:
                idx1 = int(t) - 1
            except ValueError:
                continue
            if 0 <= idx1 < n_items and idx1 not in seen:
                seen.add(idx1); out.append(idx1)
    return out

def _summarize_1based(indices_0b):
    if not indices_0b:
        return ""
    ids = [i + 1 for i in indices_0b]
    runs, start, prev = [], ids[0], ids[0]
    for k in ids[1:]:
        if k == prev + 1:
            prev = k
        else:
            runs.append((start, prev)); start = prev = k
    runs.append((start, prev))
    parts = [f"{a}-{b}" if a != b else f"{a}" for a, b in runs]
    return ",".join(parts)

class FreeChoiceAveraging(api.ProcessingNode):
    def __init__(self, nodegraph, id):
        self.meta_info = {
            "label": "Free-Choice Averaging",
            "author": "CIBM",
            "description": ("Average user-selected transients into blocks. "
                            "Each 'Group' box defines one averaged block; "
                            "accepts comma-separated indices and ranges "
                            "like '1:16, 20, 25-30'. Indices are 1-based.")
        }
        max_groups = 20
        self.parameters = [
            api.IntegerProp(
                idname="Number of groups",
                default=2, min_val=1, max_val=max_groups,
                fpb_label="How many blocks (boxes) to average"
            ),
            api.IntegerProp(
                idname="Write index files",
                default=1, min_val=0, max_val=1,
                fpb_label="Write a .txt per block (1=yes, 0=no)"
            ),
            api.StringProp(
                idname="Index files folder",
                default="",
                fpb_label="Folder for Block*.txt (empty=auto)"
            ),
        ]
        for g in range(1, max_groups + 1):
            self.parameters.append(
                api.StringProp(
                    idname=f"Group {g}",
                    default="",
                    fpb_label=f"Indices for Block {g} (e.g., 1:16, 20, 25-30)"
                )
            )
        super().__init__(nodegraph, id)

    def _resolve_index_folder(self, data):
        explicit = self.get_parameter("Index files folder")
        if explicit and explicit.strip():
            return explicit
        for k in ("outdir", "workdir"):
            v = data.get(k, None)
            if isinstance(v, str) and v.strip():
                return v
        return None

    def _write_block_txt(self, folder, block_name, idxs_0b):
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{block_name}.txt")
        one_based = [i + 1 for i in idxs_0b]
        summary = _summarize_1based(idxs_0b)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{block_name}\n")
            f.write(f"count: {len(one_based)}\n")
            f.write(f"indices_1based: {one_based}\n")
            f.write(f"ranges: {summary}\n")

    def process(self, data):
        inp = data.get("input", None)
        if inp is None or len(inp) == 0:
            raise RuntimeError("FreeChoiceAveraging: input is empty.")

        n_items = len(inp)
        n_groups = self.get_parameter("Number of groups")
        write_txt = bool(self.get_parameter("Write index files"))
        idx_folder = self._resolve_index_folder(data) if write_txt else None

        output, labels, indices_all = [], [], []

        block_idx = 0
        for g in range(1, n_groups + 1):
            spec = self.get_parameter(f"Group {g}")
            idxs = _parse_index_spec(spec, n_items)
            if not idxs:
                continue

            to_avg = [inp[i] for i in idxs if inp[i] is not None]
            if not to_avg:
                continue

            avg = np.mean(to_avg, axis=0)
            out_spec = to_avg[0].inherit(avg)

            block_idx += 1
            block_name = f"Block{block_idx}"

            output.append(out_spec)
            labels.append(block_name)
            indices_all.append(idxs)

            if idx_folder:
                try:
                    self._write_block_txt(idx_folder, block_name, idxs)
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.warning(f"Failed writing index file for {block_name}: {e}")

        if len(output) == 0:
            valid = [x for x in inp if x is not None]
            if len(valid) == 0:
                raise RuntimeError("FreeChoiceAveraging: all input entries are None.")
            output = [valid[0].inherit(np.mean(valid, axis=0))]
            labels = ["Block1"]
            indices_all = [list(range(len(inp)))]
            if idx_folder:
                try:
                    self._write_block_txt(idx_folder, "Block1", indices_all[0])
                except Exception as e:
                    if hasattr(self, "logger"):
                        self.logger.warning(f"Failed writing index file for Block1: {e}")

        data["output"] = output
        data["labels"] = labels
        data["indices"] = indices_all

api.RegisterNode(FreeChoiceAveraging, "FreeChoiceAveraging")