"""Measure three-qubit Pauli words from computational-basis probabilities."""

import pennylane as qp
import pennylane.numpy as np


def prepare(angles):
    """Prepare the three-qubit state used by the exercise."""
    qp.RY(angles[0], wires=0)
    qp.RX(angles[1], wires=1)
    qp.RY(angles[2], wires=2)
    qp.CNOT(wires=[0, 1])
    qp.RZ(angles[3], wires=1)
    qp.CNOT(wires=[1, 2])
    qp.RX(angles[3], wires=0)


def measure_pauli_word(word, angles):
    """Return basis changes, parity signs, and the Pauli-word expectation."""
    if len(word) != 3 or any(letter not in "IXYZ" for letter in word):
        raise ValueError('word must contain exactly three characters from "I", "X", "Y", "Z"')

    basis_map = {"I": "none", "Z": "none", "X": "H", "Y": "SH"}
    basis = [basis_map[letter] for letter in word]
    participating_wires = [wire for wire, letter in enumerate(word) if letter != "I"]

    signs = [
        (-1) ** sum((outcome >> (2 - wire)) & 1 for wire in participating_wires)
        for outcome in range(8)
    ]

    dev = qp.device("default.qubit", wires=3)

    @qp.qnode(dev)
    def circuit():
        prepare(angles)
        for wire, change in enumerate(basis):
            if change == "H":
                qp.Hadamard(wires=wire)
            elif change == "SH":
                qp.adjoint(qp.S)(wires=wire)
                qp.Hadamard(wires=wire)
        return qp.probs(wires=[0, 1, 2])

    probabilities = circuit()
    value = float(np.dot(probabilities, np.array(signs)))
    return basis, signs, value
