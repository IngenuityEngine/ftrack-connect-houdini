# :copyright: Copyright (c) 2016 Postmodern Digital

import os
import hou
import ftrack
import tempfile

from ftrack_connect.ui.widget.import_asset import FtrackImportAssetDialog
from ftrack_connect.ui.widget.asset_manager import FtrackAssetManagerDialog

from ftrack_connect_houdini.connector import Connector
from ftrack_connect_houdini.ui.info import FtrackHoudiniInfoDialog
from ftrack_connect_houdini.ui.publisher import PublishAssetDialog
from ftrack_connect_houdini.ui.tasks import FtrackTasksDialog

try:
    ftrack.setup()
except:
    print 'Already connected'

connector = Connector()
connector.registerAssets()

currentEntity = ftrack.Task(
    os.getenv('FTRACK_TASKID',
              os.getenv('FTRACK_SHOTID')))


def setFrameRangeData():

    start_frame = float(os.getenv('FS'))
    end_frame = float(os.getenv('FE'))
    shot_id = os.getenv('FTRACK_SHOTID')
    shot = ftrack.Shot(id=shot_id)
    fps = shot.get('fps')
    if 'handles' in shot.keys():
        handles = float(shot.get('handles'))
    else:
        handles = 0.0

    print 'setting timeline to %s %s ' % (start_frame, end_frame)

    # add handles to start and end frame
    hsf = (start_frame - 1) - handles
    hef = end_frame + handles

    hou.setFps(fps)
    hou.setFrame(start_frame)

    try:
        if start_frame != end_frame:
            hou.hscript("tset {0} {1}".format((hsf) / fps,
                        hef / fps))
            hou.playbar.setPlaybackRange(start_frame, end_frame)
    except IndexError:
        pass


setFrameRangeData()


def writePypanel(panel_id):
    """ Write temporary xml file for pypanel """
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<pythonPanelDocument>
  <interface name="{0}" label="{0}" icon="MISC_python" help_url="">
    <script><![CDATA[

import __main__

def createInterface():

    info_view = __main__.showDialog('{0}')

    return info_view]]></script>
    <help><![CDATA[]]></help>
  </interface>
</pythonPanelDocument>"""

    xml = xml.format(panel_id)

    path = os.path.join(tempfile.gettempdir(), '%s.pypanel' % panel_id)
    if os.path.exists(path):
        pass
    else:
        f = open(path, 'w')
        f.write(xml)
        f.close()
    return path


def FtrackDialogs(panel_id):
    """ Generate Dialog and create pypannel instance """

    pan_path = writePypanel(panel_id)
    hou.pypanel.installFile(pan_path)

    ftrack_id = 'Ftrack_ID'
    panel_interface = None

    try:
        for interface, value in hou.pypanel.interfaces().items():
            if interface == panel_id:
                panel_interface = value
                break
    except hou.OperationFailed:
        print 'Something Wrong with Python Pannel'

    main_tab = hou.ui.curDesktop().findPaneTab(ftrack_id)

    if main_tab:
        panel = main_tab.pane().createTab(hou.paneTabType.PythonPanel)
        panel.showToolbar(False)
        panel.setActiveInterface(panel_interface)
    else:
        if panel_interface:
            hou.hscript("pane -S -m pythonpanel -o -n %s" % ftrack_id)
            panel = hou.ui.curDesktop().findPaneTab(ftrack_id)
            panel.showToolbar(False)
            panel.setActiveInterface(panel_interface)


def showDialog(name):
    """ Show Dialog """

    if 'info' in name:
        dialog = FtrackHoudiniInfoDialog(connector=connector)
    elif 'task' in name:
        dialog = FtrackTasksDialog(connector=connector)
    elif 'import' in name:
        dialog = FtrackImportAssetDialog(connector=connector)
    elif 'Manager' in name:
        dialog = FtrackAssetManagerDialog(connector=connector)
    else:
        dialog = PublishAssetDialog(
            currentEntity=currentEntity, connector=connector)

    return dialog
