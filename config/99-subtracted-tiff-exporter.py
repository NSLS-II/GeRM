from time import sleep
from bluesky.callbacks.broker import LiveTiffExporter
from databroker import process
from bluesky import Msg
from bluesky.plans import DeltaScanPlan, DeltaListScanPlan

RE = gs.RE  # an alias


def take_dark():
    print('closing shutter...')
    shctl1.put(0)  # close shutter
    sleep(2)
    print('taking dark frame....')
    uid, = RE(Count([pe1c]))
    print('opening shutter...')
    shctl1.put(1)
    sleep(2)
    return uid


def run(motor, x, start, stop, num_steps, loops, *, exposure=1,  **metadata):
    print('moving %s to initial position' % motor.name)
    subs = [LiveTable(['pe1_stats1_total', motor.name]),
            LivePlot('pe1_stats1_total', motor.name)]
    motor.move(x)
    pe1c.images_per_set.put(exposure // 0.1)
    dark_uid = take_dark()
    steps = loops * list(np.linspace(start, stop, num=num_steps, endpoint=True))
    plan = DeltaListScanPlan([pe1c], motor, steps)
    uid = RE(plan, subs, dark_frame=dark_uid, **metadata)
    sleep(3)
    process(db[uid], exporter)


class SubtractedTiffExporter(LiveTiffExporter):
    "Intercept images before saving and subtract dark image"

    def start(self, doc):
        # The metadata refers to the scan uid of the dark scan.
        if 'dark_frame' not in doc:
            raise ValueError("No dark_frame was recorded.")
        uid = doc['dark_frame']
        dark_header = db[uid]
        self.dark_img, = get_images(db[uid], 'pe1_image')
        super().start(doc)

    def event(self, doc):
        img = doc['data'][self.field]
        subtracted_img = img - self.dark_img
        doc['data'][self.field] = subtracted_img
        super().event(doc)

template = "/home/xf28id1/xpdUser/tiff_base/LaB6_EPICS/{start.sa_name}_{start.scan_id}_step{event.seq_num}.tif"
exporter = SubtractedTiffExporter('pe1_image', template)
