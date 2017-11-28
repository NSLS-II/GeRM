# We assume this is being run in a namespace (e.g. an IPython profile startup
# script) where an instance of databroker.Broker named `db` is already defined.


from databroker_browser.qt import BrowserWindow, CrossSection, StackViewer


def search_result(h):
    return "{start[plan_name]} ['{start[uid]:.6}']".format(**h)

def text_summary(h):
    lines = []
    lines.append('Sample Name: {}'.format(h['start'].get('sample_name')))
    return '\n'.join(lines)


def fig_dispatch(header, factory):
    plan_name = header['start']['plan_name']
    if 'pe1' in header['start']['detectors']:
        fig = factory('Image Series')
        cs = CrossSection(fig)
        sv = StackViewer(cs, db.get_images(header, 'pe1_image'))
    elif len(header['start'].get('motors', [])) == 1:
        motor, = header['start']['motors']
        main_det, *_ = header['start']['detectors']
        fig = factory("{} vs {}".format(main_det, motor))
        ax = fig.gca()
        lp = LivePlot(main_det, motor, ax=ax)
        db.process(header, lp)


def browse():
    return BrowserWindow(db, fig_dispatch, text_summary, search_result)
