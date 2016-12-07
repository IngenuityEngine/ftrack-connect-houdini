# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import os
import uuid
import urlparse

import hou
import toolutils

from ftrack_connect.connector import base as maincon
from ftrack_connect.connector import FTAssetHandlerInstance, HelpFunctions


class Connector(maincon.Connector):
    def __init__(self):
        super(Connector, self).__init__()

    @staticmethod
    def getAssets():
        '''Return the available assets in scene, return the *componentId(s)*'''
        componentIds = []

        for n in hou.node('/').allSubChildren():
            if n.parmTemplateGroup().findFolder('ftrack'):
                valueftrackId = n.parm('componentId').eval()
                if valueftrackId != '':
                    if 'ftrack://' in valueftrackId:
                        url = urlparse.urlparse(valueftrackId)
                        valueftrackId = url.netloc
                        componentIds.append((valueftrackId, n.name()))

        # print componentIds
        return componentIds

    @staticmethod
    def getFileName():
        '''Return the *current scene* name'''
        return hou.hipFile.path()

    @staticmethod
    def getMainWindow():
        return None

    @staticmethod
    def importAsset(iAObj):
        iAObj.assetName = "%s_%s_AST" % (
            iAObj.assetType.upper(),
            iAObj.assetName)
        # Check if this AssetName already exists in scene
        # Need to Done!
        assetHandler = FTAssetHandlerInstance.instance()
        importAsset = assetHandler.getAssetClass(iAObj.assetType)
        if importAsset:
            result = importAsset.importAsset(iAObj)
            return result
        else:
            return 'assetType not supported'

    @staticmethod
    def selectObject(applicationObject=''):
        for n in hou.node('/').allSubChildren():
            if n.name() == applicationObject:
                n.setSelected(1, True)

    @staticmethod
    def selectObjects(selection):
        '''Return the selected nodes'''
        return hou.selectedNodes()

    @staticmethod
    def removeObject(applicationObject=''):
        for n in hou.node('/').allSubChildren():
            if n.name() == applicationObject:
                n.destroy()

    @staticmethod
    def changeVersion(applicationObject=None, iAObj=None):
        assetHandler = FTAssetHandlerInstance.instance()
        changeAsset = assetHandler.getAssetClass(iAObj.assetType)
        if changeAsset:
            result = changeAsset.changeVersion(
                iAObj, applicationObject
            )
            return result
        else:
            print 'assetType not supported'
            return False

    @staticmethod
    def getSelectedObjects():
        return hou.selectedNodes()

    @staticmethod
    def getSelectedAssets():
        selection = hou.selectedNodes()
        selectedObjects = []
        for node in selection:
            try:
                node.parm('componentId').eval()
                selectedObjects.append(node.name())
            except:
                pass
        return selectedObjects

    @staticmethod
    def setNodeColor(applicationObject='', latest=True):
        latestColor = hou.Color(hou.Vector3(0.07, 0.63, 0.29))
        oldColor = hou.Color(hou.Vector3(0.89, 0.39, 0.08))
        for n in hou.node('/').allSubChildren():
            if n.name() == applicationObject:
                if latest:
                    n.setColor(latestColor)
                else:
                    n.setColor(oldColor)

    @staticmethod
    def publishAsset(iAObj=None):
        assetHandler = FTAssetHandlerInstance.instance()
        pubAsset = assetHandler.getAssetClass(iAObj.assetType)
        if pubAsset:
            publishedComponents, message = pubAsset.publishAsset(iAObj)
            return publishedComponents, message
        else:
            return [], 'assetType not supported'

    @staticmethod
    def getConnectorName():
        '''Return the connector name'''
        return 'houdini'

    @staticmethod
    def getUniqueSceneName(assetName):
        assetName = assetName
        for n in hou.node('/').allSubChildren():
            if n.name().startswith(
                    HelpFunctions.safeString(assetName)):
                if n:
                    i = 0
                    while n:
                        uniqueAssetName = assetName + str(i)
                        if n.name().startswith(
                                HelpFunctions.safeString(uniqueAssetName)):
                            i = i + 1
                    return uniqueAssetName
                else:
                    return assetName

    @classmethod
    def registerAssets(cls):
        '''Register all the available assets'''
        import houdiniassets
        houdiniassets.registerAssetTypes()
        super(Connector, cls).registerAssets()

    @staticmethod
    def executeInThread(function, arg):
        function(arg)

    # Make certain scene validations before actualy publishing
    @classmethod
    def prePublish(cls, iAObj, assetType=''):
        '''Pre Publish check for given *iAObj*'''
        result, message = super(Connector, cls).prePublish(iAObj)
        if not result:
            return result, message

        nodes = hou.selectedNodes()
        if len(nodes) == 0:
            if (
                'exportMode' in iAObj.options and
                iAObj.options['exportMode'] == 'Selection'
            ):
                return None, 'Nothing selected'
            if (
                'alembicExportMode' in iAObj.options and
                iAObj.options['alembicExportMode'] == 'Selection'
            ):
                return None, 'Nothing selected'
        elif assetType == 'cam':
            if len(nodes) != 1:
                return None, 'Select Only One Camera Object'
            elif len(nodes) == 1 and ('cam' not in nodes[0].type().name()):
                return None, 'Select Camera Object'

        return True, ''

    @staticmethod
    def takeScreenshot():
        '''Take a screenshot and save it in the temp folder'''
        import tempfile

        res = [1024, 768]

        filename = "%s.jpg" % (os.path.join(
            tempfile.gettempdir(), str(uuid.uuid4())))

        desktop = hou.ui.curDesktop()
        scene_view = toolutils.sceneViewer()

        if scene_view is None or (
                scene_view.type() != hou.paneTabType.SceneViewer):
            raise hou.Error("No scene view available to flipbook")
        viewport = scene_view.curViewport()

        if viewport.camera() is not None:
            res = [viewport.camera().parm('resx').eval(),
                   viewport.camera().parm('resy').eval()]

        view = '%s.%s.world.%s' % (
            desktop.name(), scene_view.name(), viewport.name())

        executeCommand = "viewwrite -c -f 0 1 -r %s %s %s %s" % (
            res[0], res[1], view, filename)

        hou.hscript(executeCommand)
        return filename
