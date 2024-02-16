import matplotlib.pyplot as plt

class MatplotlibVisualization:
    """
    Interactive / real-time 3D line & point visualization using Matplotlib.
    This is quite far from the comfort zone of MPL and not very extensible.
    """
    def __init__(self):
        from mpl_toolkits.mplot3d import Axes3D
        from matplotlib.animation import FuncAnimation

        fig = plt.figure()
        ax = Axes3D(fig, auto_add_to_figure=False)
        fig.add_axes(ax)

        ax_bounds = (-0.5, 0.5) # meters
        ax.set(xlim=ax_bounds, ylim=ax_bounds, zlim=ax_bounds)
        ax.view_init(azim=-140) # initial plot orientation

        empty_xyz = lambda: { c: [] for c in 'xyz' }

        vio_data = empty_xyz()
        vio_data['plot'] = ax.plot(
            xs=[], ys=[], zs=[],
            linestyle="-",
            marker="",
            label='VIO trajectory'
        )

        vio_cam_data = empty_xyz()
        vio_cam_data['plot'] = ax.plot(
            xs=[], ys=[], zs=[],
            linestyle="-",
            marker="",
            label='current cam pose'
        )

        detection_data = empty_xyz()
        detection_data['labels'] = []
        detection_data['plot'] = ax.plot(
            xs=[], ys=[], zs=[],
            linestyle="",
            marker="o",
            label=' or '.join(SELECTED_LABELS)
        )

        ax.legend()
        ax.set_xlabel("x (m)")
        ax.set_ylabel("y (m)")
        ax.set_zlabel("z (m)")

        #title = ax.set_title("Spatial AI demo")
        def on_close(*args):
            self.should_close = True

        fig.canvas.mpl_connect('close_event', on_close)

        self.cam_wire = make_camera_wireframe()
        self.vio_data = vio_data
        self.vio_cam_data = vio_cam_data
        self.detection_data = detection_data
        self.should_close = False

        def update_graph(*args):
            r = []
            for graph in [self.vio_data, self.vio_cam_data, self.detection_data]:
                p = graph['plot'][0]
                x, y, z = [np.array(graph[c]) for c in 'xyz']
                p.set_data(x, y)
                p.set_3d_properties(z)
                r.append(p)
            return tuple(r)

        self._anim = FuncAnimation(fig, update_graph, interval=15, blit=True)

    def update_vio(self, vio_out):
        if self.should_close: return False
        view_mat = vio_out.pose.asMatrix()

        for c in 'xyz': self.vio_cam_data[c] = []
        for vertex in self.cam_wire:
            p_local = np.array(vertex + [1])
            p_world = (view_mat @ p_local)[:3]
            for i, c in enumerate('xyz'):
                self.vio_cam_data[c].append(p_world[i])

        for c in 'xyz':
            self.vio_data[c].append(getattr(vio_out.pose.position, c))

        return True

    def update_detected_objects(self, tracked_objects):
        if self.should_close: return False

        for i in range(3):
            self.detection_data['xyz'[i]] = np.array([o.position[i] for o in tracked_objects])
        self.detection_data['labels'] = [o.label for o in tracked_objects]

        return True

    def start_in_parallel_with(self, parallel_thing):
        thread = threading.Thread(target = parallel_thing, daemon=True)
        thread.start()
        plt.show()
        thread.join()