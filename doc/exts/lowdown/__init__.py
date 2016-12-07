# :coding: utf-8
# :copyright: Copyright (c) 2014 ftrack

import os
import pkgutil

import docutils.parsers.rst
import docutils.parsers.rst.directives
import docutils.nodes
import arrow

from ._version import __version__


def comma_separated_list(argument):
    '''Return comma separated string *argument* as list.'''
    return [
        part.strip() for part in argument.split(',')
        if part.strip()
    ]


def potential_link(value, link=None):
    '''Return node to represent *value*.

    If *link* is specified return a reference node. *link* can be either:

    * callable - Called with *value* to create a URI.
    * string - Formatted against value. Should contain {value}.

    Otherwise return an inline node.

    '''
    if link is None:
        # Plain inline node.
        node = docutils.nodes.inline(text=value)
    else:
        # Link.
        if callable(link):
            uri = link(value)
        else:
            uri = link.format(value=value)

        node = docutils.nodes.reference(
            '', value, refuri=uri, classes=['lowdown-link']
        )

    return node


class ReleaseDirective(docutils.parsers.rst.Directive):
    '''Release directive.

    Mark a new release in the changelog. A release should be specified with a
    version number and an optional release data::

        .. release:: 0.1.1
            :date: 2014-12-02

    Date can be specified in any format accepted by the :mod:`arrow` library.

    Each release can contain multiple :class:`ChangeDirective` instances that
    detail each change included in the release::

        .. release:: 0.1.0
            :date: 2015-01-01

            .. change:: new

                Support specifying individual changes.

    '''

    has_content = True
    required_arguments = 1
    optional_arguments = 0
    option_spec = {
        'date': docutils.parsers.rst.directives.unchanged_required
    }

    def run(self):
        '''Process directive.'''
        env = self.state.document.settings.env

        version = self.arguments[0]
        release_date = arrow.get(self.options.get('date'))

        # Section title (with link if appropriate).
        version_node = potential_link(
            version, env.config['lowdown_release_link']
        )

        section_title = docutils.nodes.title(
            '', '', version_node
        )

        # Section.
        section_id = 'release-{0}'.format(version.replace(' ', '-'))
        section = docutils.nodes.section(
            '',
            section_title,
            ids=[section_id],
            classes=['lowdown-release']
        )

        if release_date:
            section.append(
                docutils.nodes.emphasis(
                    text='{0}'.format(
                        release_date.format(env.config['lowdown_date_format'])
                    ),
                    classes=['release-date']
                )
            )

        # Content
        node = docutils.nodes.Element()
        node.document = self.state.document
        self.state.nested_parse(self.content, self.content_offset, node)

        entries = []
        for index, child in enumerate(node):
            if isinstance(child, ChangeNode):
                entry = docutils.nodes.list_item('')
                entry.append(child)
                entries.append(entry)

        section.append(
            docutils.nodes.bullet_list(
                '', *entries,
                classes=['lowdown-change-list']
            )
        )

        return [section]


class ChangeDirective(docutils.parsers.rst.Directive):
    '''Change directive.

    Mark a specific change in the changelog. Each change can specify an optional
    category::

        .. change category

            Details about change.

    In addition, each change can provide optional information:

    * tags - A comma separated list of tags used to help classify the change.
    * changelist - A changelist reference to link to source control. Combined
      with *lowdown_changelist_link* configuration option.

    '''

    has_content = True
    optional_arguments = 1
    option_spec = {
        'changeset': docutils.parsers.rst.directives.unchanged_required,
        'tags': comma_separated_list
    }

    def run(self):
        '''Process directive.'''
        env = self.state.document.settings.env

        # Main container node.
        node = ChangeNode()

        # Prefix with category.
        category = None
        if self.arguments:
            category = self.arguments[0]

        if category:
            node.append(
                docutils.nodes.inline(
                    '', category,
                    classes=[
                        'lowdown-category',
                        'lowdown-category-{0}'.format(
                            category.lower().replace(' ', '-')
                        )
                    ]
                )
            )
            node.append(docutils.nodes.Text(' '))

        # Main content.
        content = docutils.nodes.container()
        self.state.nested_parse(self.content, 0, content)
        node.append(content)
        node.append(docutils.nodes.Text(' '))

        # Insert tags into first child of main content.
        tags = self.options.get('tags')
        if tags:
            # Retrieve first paragraph or insert one if no paragraph exists.
            first_child = None
            if len(content.children):
                first_child = content.children[0]
            if (
                first_child is None
                or not isinstance(first_child, docutils.nodes.paragraph)
            ):
                first_child = docutils.nodes.paragraph()
                content.insert(0, first_child)

            tags = sorted(set(tags), reverse=True)
            for tag in tags:
                first_child.insert(
                    0,
                    docutils.nodes.inline(
                        '', text=tag,
                        classes=[
                            'lowdown-tag',
                            'lowdown-tag-{0}'.format(
                                tag.lower().replace(' ', '-')
                            )
                        ]
                    )
                )

        # Insert changeset link to last child of main content.
        changeset = self.options.get('changeset')
        if changeset:
            changeset_node = potential_link(
                changeset, env.config['lowdown_changeset_link']
            )
            changeset_node['classes'].append('lowdown-changeset')

            # Retrieve last paragraph or insert one if no paragraph exists.
            last_child = None
            if len(content.children):
                last_child = content.children[-1]
            if (
                last_child is None
                or not isinstance(last_child, docutils.nodes.paragraph)
            ):
                last_child = docutils.nodes.paragraph()
                content.append(last_child)

            last_child.append(docutils.nodes.Text(' '))
            last_child.append(changeset_node)

        return [node]


class ChangeNode(docutils.nodes.paragraph):
    '''Represent a specific change.'''

    def __init__(self, *args, **kwargs):
        '''Initialise node.'''
        kwargs.setdefault('classes', [])
        kwargs['classes'].append('lowdown-change')
        docutils.nodes.TextElement.__init__(self, *args, **kwargs)


def visit_change_node_html(self, node):
    '''Visit :class:`ChangeNode`.'''
    self.body.append(self.starttag(node, 'div', CLASS='lowdown-change'))


def depart_change_node_html(self, node):
    '''Depart :class:`ChangeNode`.'''
    self.body.append('</div>\n')


def add_stylesheet(application):
    '''Add default stylesheet to *application*.'''
    application.add_stylesheet('lowdown.css')


def copy_stylesheet(app, exception):
    '''Copy stylesheet to output when building html.'''
    if app.builder.name not in ('html', 'readthedocs') or exception:
        return

    source = pkgutil.get_data('lowdown', 'lowdown.css')
    target = os.path.join(app.builder.outdir, '_static', 'lowdown.css')
    with open(target, 'w') as file_object:
        file_object.write(source)


def setup(app):
    '''Register extension with Sphinx.'''
    app.add_config_value('lowdown_date_format', 'D MMMM YYYY', 'env')
    app.add_config_value('lowdown_release_link', None, 'env')
    app.add_config_value('lowdown_changeset_link', None, 'env')

    app.add_node(
        ChangeNode,
        html=(visit_change_node_html, depart_change_node_html)
    )
    app.add_directive('release', ReleaseDirective)
    app.add_directive('change', ChangeDirective)

    app.connect('builder-inited', add_stylesheet)
    app.connect('build-finished', copy_stylesheet)
