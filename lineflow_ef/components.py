"""
Module containing custom simulation components for the lineflow_ef package.
"""

from lineflow.simulation import (
    Source,
    Sink
)
from lineflow.simulation.states import (
    TokenState,
    DiscreteState,
    ObjectStates
)
from lineflow_ef.helpers import (
    ComponentSampler,
    build_idle_carrier_spec
)

from typing import List, Dict, Optional, Tuple
import numpy as np


class AlternatingSource(Source):
    """
    Source capable of creating the worksteps for the machines, adding them
    to the machine_list.
    Allows agent to change order of machine_list and add empty carriers.
    """

    def __init__(self, name, *args, **kwargs):
        super().__init__(name=name, *args, carrier_capacity=70,  **kwargs)

        self.pk_len = 10

        self.machine_list: List[Dict] = []
        for _ in range(self.pk_len):
            mtype, cid, wsteps = self._sample_machine_spec()
            self.machine_list.append({"machine_type": mtype, "config_id": cid, "worksteps": wsteps})

        self._last_issued_label: Optional[str] = None

    def _sample_machine_spec(self) -> Tuple[str, int, Dict]:
        machine_type, config_id, machine_worksteps = ComponentSampler()
        return machine_type, config_id, machine_worksteps

    def init_state(self):
        pk_len = getattr(self, "pk_len", 10)

        base_states = [
            DiscreteState('on', categories=[True, False], is_actionable=False, is_observable=False),
            DiscreteState('mode', categories=['working', 'waiting', 'failing']),
            DiscreteState(
                name='waiting_time',
                categories=np.arange(0, 100, self.waiting_time_step),
                is_actionable=False,
            ),
            TokenState(name='carrier', is_observable=False),
            TokenState(name='part', is_observable=False),

            DiscreteState(
                name='config_id',
                categories=list(range(0, 10_000_000)),
                is_actionable=False,
                is_observable=True,
            ),
            DiscreteState(
                name='carrier_spec',
                categories=["Type_1", "Type_2", "Type_3", "no_name"],
                is_actionable=False,
                is_observable=True,
            ),
            DiscreteState(
                name='pk_pick',
                categories=list(range(0, pk_len + 1)),
                is_actionable=True,
                is_observable=False,
            ),
            DiscreteState(
                name='inject_idle',
                categories=[0, 1],
                is_actionable=True,
                is_observable=False,
            ),
        ]

        pk_preview_states = [
            DiscreteState(
                name=f'pk_id_{i}',
                categories=list(range(0, 10_000_000)),
                is_actionable=False,
                is_observable=True,
            )
            for i in range(pk_len)
        ]

        self.state = ObjectStates(*(base_states + pk_preview_states))

        self.state['waiting_time'].update(self.init_waiting_time)
        self.state['on'].update(True)
        self.state['mode'].update("waiting")
        self.state['carrier'].update(None)
        self.state['part'].update(None)
        self.state["carrier_spec"].update("no_name")
        self.state["config_id"].update(0)
        self.state["pk_pick"].update(pk_len)
        self.state["inject_idle"].update(0)

        self._update_pk_preview_states()

    def _update_pk_preview_states(self):
        for i in range(self.pk_len):
            cid = int(self.machine_list[i]["config_id"])
            self.state[f"pk_id_{i}"].update(cid)

    def _issue_idle(self) -> Dict:
        mtype, cid, wsteps = build_idle_carrier_spec()
        self._last_issued_label = next(iter(wsteps.keys())) if wsteps else None
        self.state["carrier_spec"].update(mtype)
        self.state["config_id"].update(int(cid))
        return wsteps

    def _issue_from_machine_list(self) -> Dict:

        pick_raw = int(self.state["pk_pick"].value)
        K = self.pk_len
        idx = 0 if pick_raw >= K else pick_raw
        idx = max(0, min(idx, K-1))

        chosen = self.machine_list.pop(idx)
        wsteps = chosen["worksteps"]
        self._last_issued_label = next(iter(wsteps.keys())) if wsteps else None

        self.state["carrier_spec"].update(chosen["machine_type"])
        self.state["config_id"].update(int(chosen["config_id"]))

        mtype, cid, nw = self._sample_machine_spec()
        self.machine_list.append({"machine_type": mtype, "config_id": cid, "worksteps": nw})

        self._update_pk_preview_states()

        self.state["pk_pick"].update(K)
        self.state["inject_idle"].update(0)

        return wsteps

    def get_current_carrier_spec(self) -> Dict:

        inject = int(self.state["inject_idle"].value)
        if inject == 1:
            return self._issue_idle()
        else:
            return self._issue_from_machine_list()

    def assemble_parts_on_carrier(self, carrier, parts):

        super().assemble_parts_on_carrier(carrier, parts)

        current_carrier_number = carrier.specs['name'].rsplit('_',2)[1] \
            if 'C_' in carrier.specs['name'] else carrier.specs['name'].rsplit('_',1)[1]

        if self._last_issued_label:
            label = str(self._last_issued_label).rsplit('_', 2)[0]
        else:
            label = "no_name"

        carrier.specs['name'] = f"C_{current_carrier_number}_{label}"


class CustomSink(Sink):
    """
    Custom addaption of Sink for not counting empty carriers as produced parts.
    """

    def remove(self, carrier):

        processing_time = self._sample_exp_time(
            time=self.processing_time,
            scale=self.processing_std,
        )
        yield self.env.timeout(processing_time)

        name = str(carrier.specs.get('name', '')).lower()
        if 'leer' not in name:
            self.state['n_parts_produced'].increment()

        if hasattr(self, 'buffer_out'):
            yield self.env.process(self.set_to_waiting())
            carrier.parts.clear()
            yield self.env.process(self.buffer_out(carrier))
