# SeqAssignLine

Code Repository for experimenting with the [`LineFlow`](https://hs-kempten.github.io/lineflow/) framework to simulate a large-scale sequential
assembly line. The actions space includes $10^{43}$ possible discrete actions, pushing the limits of current RL-models.

![LineFlow EF](./docs/figures/layout.png)

# Install

Install with

```bash
pip install .
```

# Usage


```python
from lineflow_ef import Seq_Pro_Assembly

line = Seq_Pro_Assembly()
line.run(3000, visualize=True)
```



## Use in LineFlow


```python
from lineflow.simulation import LineSimulation

env = LineSimulation(line, simulation_end=10_000)
