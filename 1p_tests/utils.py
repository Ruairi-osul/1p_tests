import isx
from pathlib import Path


class SessionAutoProcessor:
    def __init__(self, raw_data_path: str):
        self.raw_data_path = Path(raw_data_path)
        self.recording_name = self.raw_data_path.name.split(".")[0]
        self.raw_data_dir = raw_data_path.parent
        self.processed_data_dir = self.raw_data_dir / (
            self.recording_name + "_processed"
        )
        self.processed_data_dir.mkdir(exist_ok=True)
        self.exports_dir = self.processed_data_dir / "exports"
        self.exports_dir.mkdir(exist_ok=True)
        self.cell_image_exports_dir = self.exports_dir / "cell_images"
        self.cell_image_exports_dir.mkdir(exist_ok=True)

    def _make_fn(self, fn, d=None):
        if d is None:
            d = self.processed_data_dir
        fn = d / fn
        if fn.exists():
            fn.unlink()
        return fn

    def preprocess(self):
        self.pp_file = self._make_fn("01-preprocessed.isxd")
        return isx.preprocess(str(self.raw_data_path), str(self.pp_file))

    def spatial_filter(self):
        self.sf_file = self._make_fn("02-spatially_filtered.isxd")
        return isx.spatial_filter(str(self.pp_file), str(self.sf_file))

    def motion_correct(self):
        self.mc_file = self._make_fn("03-motion_corrected.isxd")
        return isx.motion_correct(str(self.sf_file), str(self.mc_file))

    def get_dff(self):
        self.dff_file = self._make_fn("04-dff.isxd")
        return isx.dff(str(self.mc_file), str(self.dff_file))

    def run_pca_ica(
        self, num_pcs=150, num_ics=None, filters=None, auto_accept_reject=True
    ):
        if filters is None:
            filters = [
                ("# Comps", "=", 1),
                ("Cell Size", ">", 7),
                ("Cell Size", "<", 70),
                ("SNR", ">", 3),
            ]
        self.pca_file = self._make_fn("05-pca_ica.isxd")
        self.num_pcs = num_pcs
        self.num_ics = num_ics if num_ics is not None else int(num_pcs * 1.15)
        self.cell_events_file = self._make_fn("06-events.isxd")
        isx.pca_ica(str(self.dff_file), str(self.pca_file), self.num_pcs, self.num_ics)
        if auto_accept_reject:
            isx.event_detection(str(self.pca_file), str(self.cell_events_file))
            isx.auto_accept_reject(
                str(self.pca_file), str(self.cell_events_file), filters
            )

    def export_data(self):
        trace_file = self._make_fn("traces.csv", d=self.exports_dir)
        average_image_file = self._make_fn("average_image.png", d=self.exports_dir)
        contour_file = self._make_fn("cell_contours.json", d=self.exports_dir)
        cell_images = self._make_fn("images.tiff", self.cell_image_exports_dir)
        cell_events_file = self._make_fn("cell_events", self.exports_dir)

        isx.export_cell_contours(str(self.pca_file), str(contour_file))
        isx.export_cell_set_to_csv_tiff(
            str(self.pca_file), str(trace_file), str(cell_images)
        )
        isx.export_event_set_to_csv(str(self.cell_events_file), str(cell_events_file))
        isx.project_movie(str(self.dff_file), str(average_image_file), stat_type="max")

