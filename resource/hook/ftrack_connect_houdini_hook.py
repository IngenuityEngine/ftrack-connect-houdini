# :coding: utf-8
# :copyright: Copyright (c) 2015 ftrack

import getpass
import sys
import pprint
import logging
import re
import os

# RESOURCE_DIRECTORY = os.path.abspath(
#     os.path.join(os.path.dirname(__file__), '..', 'resource')
# )

# if RESOURCE_DIRECTORY not in sys.path:
#     sys.path.append(RESOURCE_DIRECTORY)

import ftrack
import ftrack_connect.application
import ftrack_connect_houdini


class HoudiniAction(object):
    '''Launch Houdini action.'''

    # Unique action identifier.
    identifier = 'ftrack-connect-launch-houdini'

    def __init__(self, applicationStore, launcher):
        '''Initialise action with *applicationStore* and *launcher*.

        *applicationStore* should be an instance of
        :class:`ftrack_connect.application.ApplicationStore`.

        *launcher* should be an instance of
        :class:`ftrack_connect.application.ApplicationLauncher`.

        '''
        super(HoudiniAction, self).__init__()

        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

        self.applicationStore = applicationStore
        self.launcher = launcher

        if self.identifier is None:
            raise ValueError('The action must be given an identifier.')

    def is_valid_selection(self, selection):
        '''Return true if the selection is valid.'''
        if (
            len(selection) != 1 or
            selection[0]['entityType'] != 'task'
        ):
            return False

        entity = selection[0]
        task = ftrack.Task(entity['entityId'])

        if task.getObjectType() != 'Task':
            return False

        return True

    def register(self):
        '''Register action to respond to discover and launch events.'''
        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(
                getpass.getuser()
            ),
            self.discover
        )

        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.launch and source.user.username={0} '
            'and data.actionIdentifier={1}'.format(
                getpass.getuser(), self.identifier
            ),
            self.launch
        )

        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.connect.plugin.debug-information',
            self.get_version_information
        )

    def discover(self, event):
        '''Return discovered applications.'''

        if not self.is_valid_selection(
            event['data'].get('selection', [])
        ):
            return

        items = []
        applications = self.applicationStore.applications
        applications = sorted(
            applications, key=lambda application: application['label']
        )

        for application in applications:
            applicationIdentifier = application['identifier']
            label = application['label']
            items.append({
                'actionIdentifier': self.identifier,
                'label': label,
                'variant': application.get('variant', None),
                'icon': 'https://drive.google.com/uc?export=download&confirm=no_antivirus&id=0BxXE88V3yaEMdy1IdURJaTdwcFU',
                'applicationIdentifier': applicationIdentifier
            })

        return {
            'items': items
        }

    def launch(self, event):
        '''Callback method for Houdini action.'''
        # applicationIdentifier = (
        #     event['data']['applicationIdentifier']
        # )

        # context = event['data'].copy()

        # return self.launcher.launch(
        #     applicationIdentifier, context
        # )
        #########################################
        event.stop()

        if not self.is_valid_selection(
            event['data'].get('selection', [])
        ):
            return

        application_identifier = (
            event['data']['applicationIdentifier']
        )

        context = event['data'].copy()
        context['source'] = event['source']

        application_identifier = event['data']['applicationIdentifier']
        context = event['data'].copy()
        context['source'] = event['source']

        return self.launcher.launch(
            application_identifier, context
        )

    def get_version_information(self, event):
        '''Return version information.'''
        return dict(
            name='ftrack connect houdini',
            version=ftrack_connect_houdini.__version__
        )


class ApplicationStore(ftrack_connect.application.ApplicationStore):
    '''Store used to find and keep track of available applications.'''

    def _discoverApplications(self):
        '''Return a list of applications that can be launched from this host.
        '''
        applications = []

        if sys.platform == 'darwin':
            prefix = ['/', 'Applications']

            applications.extend(self._searchFilesystem(
                expression=prefix + [
                    'Houdini*', 'Houdini.app'
                ],
                label='Houdini {version}',
                icon='houdini',
                applicationIdentifier='houdini_{version}'
            ))

        elif 'linux' in sys.platform:
            prefix = ['/', 'opt']

            applications.extend(self._searchFilesystem(
                expression=prefix + [
                    'hfs*', 'bin', 'houdinifx-bin'
                ],
                label='Houdini',
                variant='{version}',
                icon='houdini',
                applicationIdentifier='houdini_{version}'
            ))

        elif sys.platform == 'win32':
            prefix = ['C:\\', 'Program Files.*']

            applications.extend(self._searchFilesystem(
                expression=(
                    prefix +
                    ['Side Effects Software', 'Houdini*', 'bin', 'houdini.exe']
                ),
                label='Houdini {version}',
                icon='houdini',
                applicationIdentifier='houdini_{version}'
            ))

        self.logger.debug(
            'Discovered applications:\n{0}'.format(
                pprint.pformat(applications)
            )
        )

        return applications


class ApplicationLauncher(ftrack_connect.application.ApplicationLauncher):
    '''Custom launcher to modify environment before launch.'''
    def __init__(self, application_store, plugin_path):
        '''.'''
        super(ApplicationLauncher, self).__init__(application_store)

        self.plugin_path = plugin_path

    def _getApplicationEnvironment(
        self, application, context=None
    ):
        '''Override to modify environment before launch.'''

        # Make sure to call super to retrieve original environment
        # which contains the selection and ftrack API.
        environment = super(
            ApplicationLauncher, self
        )._getApplicationEnvironment(application, context)

        entity = context['selection'][0]
        task = ftrack.Task(entity['entityId'])
        taskParent = task.getParent()

        try:
            environment['FS'] = str(int(taskParent.getFrameStart()))
        except Exception:
            environment['FS'] = '1'

        try:
            environment['FE'] = str(int(taskParent.getFrameEnd()))
        except Exception:
            environment['FE'] = '1'

        environment['FTRACK_TASKID'] = task.getId()
        environment['FTRACK_SHOTID'] = task.get('parent_id')

        # houdini_connect_scripts = os.path.join(self.plugin_path, 'scripts')
        # houdini_connect_plugins = os.path.join(self.plugin_path, 'plug_ins')

        # Append or Prepend values to the environment.
        # Note that if you assign manually you will overwrite any
        # existing values on that variable.

        # Add my custom path to the HOUDINI_SCRIPT_PATH.
        environment = ftrack_connect.application.appendPath(
            os.path.pathsep.join([self.plugin_path, '&']),
            'HOUDINI_PATH',
            environment
        )

        environment = ftrack_connect.application.appendPath(
            self.plugin_path,
            'PYTHONPATH',
            environment
        )

        environment = ftrack_connect.application.appendPath(
            os.path.join(self.plugin_path, '..', 'resource'),
            'PYTHONPATH',
            environment
        )
        # Always return the environment at the end.
        return environment


def register(registry, **kw):
    '''Register hooks.'''

    # Validate that registry is the correct ftrack.Registry. If not,
    # assume that register is being called with another purpose or from a
    # new or incompatible API and return without doing anything.
    if registry is not ftrack.EVENT_HANDLERS:
        # Exit to avoid registering this plugin again.
        return

    # Create store containing applications.
    application_store = ApplicationStore()

    # Create a launcher with the store containing applications.
    launcher = ApplicationLauncher(
        application_store, plugin_path=os.environ.get(
            'FTRACK_CONNECT_HOUDINI_PLUGINS_PATH',
            os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__), '..', 'ftrack_connect_houdini'
                )
            )
        )
    )

    # Create action and register to respond to discover and launch actions.
    action = HoudiniAction(application_store, launcher)
    action.register()


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.INFO)

    # Create store containing applications.
    applicationStore = ApplicationStore()

    # Create a launcher with the store containing applications.
    launcher = ftrack_connect.application.ApplicationLauncher(
        applicationStore
    )

    # Create action and register to respond to discover and launch actions.
    ftrack.setup()
    action = HoudiniAction(applicationStore, launcher)
    action.register()

    import app_launch_environment

    ftrack.EVENT_HUB.subscribe(
        'topic=ftrack.connect.application.launch',
        app_launch_environment.modify_application_launch)

    ftrack.EVENT_HUB.wait()