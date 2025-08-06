import processing.api as api
import numpy as np
import re

def _parse_index_spec(spec_str, n_items):
    """
    Parse a user string like '1:16, 20, 25-30, 42' into a list of unique
    zero-based indices within [0, n_items-1], preserving first-seen order.
    Supports ':' or '-' as range delimiters. 1-based input -> 0-based output.
    """
    if not spec_str or not spec_str.strip():
        return []

    tokens = re.split(r'[,\s]+', spec_str.strip())
    out = []
    seen = set()

    for tok in tokens:
        if not tok:
            continue
        # Normalize range delimiter
        t = tok.replace('-', ':')
        if ':' in t:
            parts = t.split(':')
            if len(parts) != 2:
                continue
            try:
                start = int(parts[0])
                end = int(parts[1])
            except ValueError:
                continue
            # 1-based -> 0-based, inclusive range
            lo = min(start, end) - 1
            hi = max(start, end) - 1
            for idx in range(lo, hi + 1):
                if 0 <= idx < n_items and idx not in seen:
                    seen.add(idx)
                    out.append(idx)
        else:
            try:
                idx1 = int(t) - 1  # 1-based -> 0-based
            except ValueError:
                continue
            if 0 <= idx1 < n_items and idx1 not in seen:
                seen.add(idx1)
                out.append(idx1)
    return out

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
        # Config: how many GUI boxes to show for grouping
        # (We expose a 'Number of groups' and up to 20 Group boxes.)
        max_groups = 20
        self.parameters = [
            api.IntegerProp(
                idname="Number of groups",
                default=6,
                min_val=1,
                max_val=max_groups,
                fpb_label="How many blocks (boxes) to average"
            )
        ]
        # Add string boxes Group 1..Group N (N up to max_groups)
        for g in range(1, max_groups + 1):
            self.parameters.append(
                api.StringProp(
                    idname=f"Group {g}",
                    default="",
                    fpb_label=f"Indices for Block {g} (e.g., 1:16, 20, 25-30)"
                )
            )
        super().__init__(nodegraph, id)

    def process(self, data):
        inp = data.get("input", None)
        if inp is None or len(inp) == 0:
            raise RuntimeError("FreeChoiceAveraging: input is empty.")

        n_items = len(inp)
        n_groups = self.get_parameter("Number of groups")
        output = []
        labels = []

        # Build each block from the corresponding Group box
        for g in range(1, n_groups + 1):
            spec = self.get_parameter(f"Group {g}")
            idxs = _parse_index_spec(spec, n_items)

            # Skip empty groups
            if not idxs:
                continue

            # Gather spectra (skip None safely)
            to_avg = [inp[i] for i in idxs if inp[i] is not None]
            if len(to_avg) == 0:
                continue

            # Average (complex) along transient axis
            avg = np.mean(to_avg, axis=0)
            # Inherit metadata from first valid transient
            out_spec = to_avg[0].inherit(avg)

            output.append(out_spec)

            # Build a concise label
            # Example: Block1_n16(1-16) or Block2_n8(25-30,42,…) if long
            count = len(idxs)
            # Summarize indices for readability
            def summarize(idxs_1based):
                # Collapse consecutive runs into a-b
                if not idxs_1based:
                    return ""
                runs = []
                start = prev = idxs_1based[0]
                for k in idxs_1based[1:]:
                    if k == prev + 1:
                        prev = k
                    else:
                        runs.append((start, prev))
                        start = prev = k
                runs.append((start, prev))
                parts = []
                for a, b in runs:
                    parts.append(f"{a}-{b}" if a != b else f"{a}")
                s = ",".join(parts)
                # If too long, truncate
                return s if len(s) <= 20 else (s[:20] + "…")

            idxs_1b = [i + 1 for i in idxs]
            summary = summarize(idxs_1b)
            label = f"Block{len(output)}_n{count}({summary})"
            labels.append(label)

        # Fallback: if user gave no valid groups, do a grand average
        if len(output) == 0:
            valid = [x for x in inp if x is not None]
            if len(valid) == 0:
                raise RuntimeError("FreeChoiceAveraging: all input entries are None.")
            output = [valid[0].inherit(np.mean(valid, axis=0))]
            labels = ["Block1_n{0}(all)".format(len(valid))]

        data["output"] = output
        data["labels"] = labels

api.RegisterNode(FreeChoiceAveraging, "FreeChoiceAveraging")