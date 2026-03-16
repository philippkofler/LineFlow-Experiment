'''
Assembly line using the SequentialProcess.
'''

from lineflow_ef.components import (
    AlternatingSource,
    CustomSink
)
from lineflow.simulation import (
    Line,
    WorkerPool,
    Magazine,
    SequentialProcess
)
from lineflow_ef.components_dict import components_dict

class Seq_Pro_Assembly(Line):   

    def build_process(self, number, x, y):
        
        worker_pool = None
        for lo, hi, pool in self.ranges:
            if lo <= number <= hi:
                worker_pool = pool
                break
        
        return SequentialProcess(
            name=self.station_names[number-1] if number-1 < len(self.station_names) and self.station_names[number-1] else f'Takt {number}',
            worker_pool=worker_pool,
            processing_time=0,
            processing_std=0.05,
            error_std=0.2,
            position=(x, y)
        )

    def build(self):
        self.station_names = list(components_dict.keys())

        workers = [15, 5, 8, 12, 2, 2, 14]

        pools = []

        for i, n in enumerate(workers):
            pools.append(
                WorkerPool(
                    name=f'WorkerPool_{i+1}',
                    n_workers=n,
                    transition_time=20
                )
            )

        self.ranges = [
            (1, 6,  pools[0]),
            (7, 10, pools[1]),
            (11, 16, pools[2]),
            (17, 21, pools[3]),
            (22, 23, pools[4]),
            (24, 25, pools[5]),
            (26, 32, pools[6]),
        ]


        part_source = AlternatingSource(
            name='Source',
            processing_time=5,
            position=(100, 600),
            waiting_time=10,
            unlimited_carriers=False,
        )

        magazine_carrier = Magazine(
            'Carrier Control',
            unlimited_carriers=False,
            carrier_capacity=100,
            carriers_in_magazine=32,
            position=(100, 350),
            actionable_magazine=False,
        )

        x_left = 200
        x_right = 1200
        y0 = 600
        dy = -100

        rows = [
            (1, 4,  True),
            (5, 9, False),
            (11, 16,  True),
            (17, 22, False),
            (23, 28,  True),
            (29, 32, False),
        ]

        processes = []
        for r_idx, (start_i, end_i, left_to_right) in enumerate(rows):
            m = end_i - start_i + 1
            y = y0 + r_idx * dy

            if m == 1:
                xs = [(x_left + x_right) / 2.0]
            else:
                span = (x_right - x_left) / (m - 1)
                xs = [x_left + k * span for k in range(m)]

            if not left_to_right:
                xs = list(reversed(xs))

            for offset, i in enumerate(range(start_i, end_i + 1)):
                x = xs[offset]
                processes.append(self.build_process(i, x, y))

        sink = CustomSink(
            'Sink',
            position=(100, 100),
            processing_time=0
        )

        processes[0].connect_to_input(part_source)
        processes[-1].connect_to_output(sink)
        for p_prior, p_after in zip(processes[:-1], processes[1:]):
            p_prior.connect_to_output(p_after, capacity=2, transition_time=10)

        magazine_carrier.connect_to_output(part_source)
        magazine_carrier.connect_to_input(sink)


if __name__ == '__main__':
    line = Seq_Pro_Assembly(step_size=5)
    line.run(3000, visualize=True, capture_screen=True)
