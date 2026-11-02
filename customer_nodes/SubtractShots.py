import processing.api as api
import numpy as np


class SubtractShots(api.ProcessingNode):
    def __init__(self, nodegraph, id):
        self.meta_info = {
            "label": "Shot Subtraction",
            "author": "CIBM",
            "description": (
                "Subtract consecutive pairs of shots without averaging. "
                "Order 1: 1-2, 3-4, 5-6, ...; "
                "order 2: 2-1, 4-3, 6-5, ... . "
                "Requires an even number of shots and no missing shots."
            )
        }
        self.parameters = [
            api.IntegerProp(
                idname="Subtraction order",
                default=1,
                min_val=1,
                max_val=2,
                fpb_label=(
                    "1 = shots 1-2, 3-4, 5-6, ... . "
                    "2 = shots 2-1, 4-3, 6-5, ... ."
                )
            )
        ]

        super().__init__(nodegraph, id)

    def process(self, data):
        spectra = data["input"]

        if len(spectra) == 0:
            data["output"] = []
            data["labels"] = []
            return

        order = self.get_parameter("Subtraction order")
        if order not in (1, 2):
            raise ValueError("Subtraction order must be 1 or 2.")

        if len(spectra) % 2:
            raise ValueError(
                "Shot Subtraction requires an even number of shots. "
                f"Received {len(spectra)}; the last shot has no partner."
            )

        output = []
        labels = []

        for i in range(0, len(spectra), 2):
            first, second = spectra[i:i + 2]
            if first is None or second is None:
                raise ValueError(
                    f"Shots {i + 1} and {i + 2} contain a missing spectrum. "
                    "Both shots are required for pairwise subtraction."
                )

            first_values = np.asarray(first)
            second_values = np.asarray(second)
            if first_values.shape != second_values.shape:
                raise ValueError(
                    f"Shots {i + 1} and {i + 2} have different shapes: "
                    f"{first_values.shape} and {second_values.shape}."
                )

            if order == 1:
                difference = first.inherit(first_values - second_values)
                label = f"Shots{i + 1}-{i + 2}"
            else:
                difference = second.inherit(second_values - first_values)
                label = f"Shots{i + 2}-{i + 1}"

            output.append(difference)
            labels.append(label)

        data["output"] = output
        data["labels"] = labels


api.RegisterNode(SubtractShots, "SubtractShots")
